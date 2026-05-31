<?php
/**
 * API for Weights Capture (Get Weights & Update HUID Codes)
 * Used by MANAK Automation
 */

header('Content-Type: application/json');
header("Access-Control-Allow-Origin: *");
header("Access-Control-Allow-Headers: Content-Type");

// Enable error logging but disable display to prevent invalid JSON
ini_set('display_errors', 0);
ini_set('log_errors', 1);
error_reporting(E_ALL);

// Handle fatal errors
register_shutdown_function(function() {
    $error = error_get_last();
    if ($error && ($error['type'] === E_ERROR || $error['type'] === E_PARSE || $error['type'] === E_CORE_ERROR)) {
        http_response_code(500);
        header('Content-Type: application/json');
        echo json_encode(["status" => "error", "message" => "Fatal Error: " . $error['message'] . " on line " . $error['line']]);
        exit;
    }
});

// Database configuration
$servername = "localhost";
$username = "u176143338_hallmarkProver";
$password = "Rontik10@";
$dbname = "u176143338_hallmarkProver";

// Create connection
$conn = new mysqli($servername, $username, $password, $dbname);

// Check connection
if ($conn->connect_error) {
    http_response_code(500);
    echo json_encode(['status' => 'error', 'message' => 'Database connection failed: ' . $conn->connect_error]);
    exit;
}

// Set charset
$conn->set_charset("utf8mb4");

// Helper function to send JSON response
function sendResponse($status, $message, $data = null) {
    global $conn;
    $conn->close();
    echo json_encode([
        'status' => $status,
        'message' => $message,
        'data' => $data
    ]);
    exit;
}

// Get raw POST data
$jsonData = file_get_contents('php://input');
$request = json_decode($jsonData, true);

try {
    // Check if JSON decoding failed
    if (json_last_error() !== JSON_ERROR_NONE) {
        throw new Exception("Invalid JSON input: " . json_last_error_msg());
    }

    $action = $request['action'] ?? '';

    // === ACTION: Get Pending Requests (Scan Portal Merge) ===
    if ($action === 'get_pending_requests') {
        $firmId = $request['firm_id'] ?? '';
        $requestNos = $request['request_nos'] ?? []; 
        
        if (empty($firmId)) {
            sendResponse('error', 'Missing firm_id');
        }

        // If request numbers provided, filter by them
        if (!empty($requestNos)) {
            $placeholders = implode(',', array_fill(0, count($requestNos), '?'));
            $types = 's' . str_repeat('s', count($requestNos));
            $params = array_merge([$firmId], $requestNos);
            
            $sql = "SELECT id, request_no, job_no, item, pcs, purity, weight 
                    FROM job_cards 
                    WHERE firm_id = ? AND request_no IN ($placeholders)
                    ORDER BY id DESC";
            
            $stmt = $conn->prepare($sql);
            if (!$stmt) throw new Exception("Prepare failed: " . $conn->error);
            $stmt->bind_param($types, ...$params);
        } else {
            // Fetch all pending? Or recent? 
            // Usually we only need this for specific requests found on portal, so 
            // let's just return recent ones if no specific requests asked
             $sql = "SELECT id, request_no, job_no, item, pcs, purity, weight 
                    FROM job_cards 
                    WHERE firm_id = ? 
                    AND (job_no IS NULL OR job_no = '' OR job_no = '0')
                    ORDER BY id DESC LIMIT 50";
            $stmt = $conn->prepare($sql);
            if (!$stmt) throw new Exception("Prepare failed: " . $conn->error);
            $stmt->bind_param("s", $firmId);
        }

        if (!$stmt->execute()) {
            throw new Exception("Execute failed: " . $stmt->error);
        }
        
        $result = $stmt->get_result();
        $data = [];
        while ($row = $result->fetch_assoc()) {
            $data[] = $row;
        }
        $stmt->close();
        sendResponse('success', 'Fetched pending requests', $data);
    }

    // === ACTION: Get Weight Capture Jobs (API-first loading) ===
    elseif ($action === 'get_weight_capture_jobs') {
        $firmId = $request['firm_id'] ?? '';
        $material = strtolower(trim($request['material'] ?? ''));
        $dateFrom = trim($request['date_from'] ?? '');
        $dateTo = trim($request['date_to'] ?? '');
        $withHuidOnly = (int)($request['with_huid_only'] ?? 1) === 1;
        $startPage = max(1, (int)($request['page'] ?? 1));
        $endPage = max($startPage, (int)($request['page_to'] ?? $startPage));
        $pageSize = 10;
        $offset = ($startPage - 1) * $pageSize;
        $limit = max(1, ($endPage - $startPage + 1) * $pageSize);
        
        if (empty($firmId)) {
            sendResponse('error', 'Missing firm_id');
        }
        
        $sql = "SELECT 
                    jc.request_no,
                    jc.job_no,
                    jc.item,
                    jc.pcs,
                    jc.weight,
                    jc.status,
                    jc.date_of_request,
                    CASE 
                        WHEN LOWER(COALESCE(jc.item, '')) LIKE '%silver%' THEN 'Silver'
                        ELSE 'Gold'
                    END AS material,
                    (
                        SELECT COUNT(*) 
                        FROM huid_data hd 
                        WHERE hd.job_no = jc.job_no AND hd.weight > 0
                    ) AS tags_available
                FROM job_cards jc
                WHERE jc.firm_id = ?
                AND jc.job_no IS NOT NULL
                AND jc.job_no != ''
                AND jc.job_no != '0'
                AND jc.status LIKE '%Weight Capture%'";
        
        $types = "s";
        $params = [$firmId];
        
        if ($material === 'silver') {
            $sql .= " AND LOWER(COALESCE(jc.item, '')) LIKE '%silver%'";
        } elseif ($material === 'gold') {
            $sql .= " AND LOWER(COALESCE(jc.item, '')) NOT LIKE '%silver%'";
        }
        
        if (!empty($dateFrom)) {
            $sql .= " AND COALESCE(
                        STR_TO_DATE(jc.date_of_request, '%Y-%m-%d'),
                        STR_TO_DATE(jc.date_of_request, '%d/%m/%Y'),
                        STR_TO_DATE(jc.date_of_request, '%d-%m-%Y')
                    ) >= STR_TO_DATE(?, '%Y-%m-%d')";
            $types .= "s";
            $params[] = $dateFrom;
        }
        
        if (!empty($dateTo)) {
            $sql .= " AND COALESCE(
                        STR_TO_DATE(jc.date_of_request, '%Y-%m-%d'),
                        STR_TO_DATE(jc.date_of_request, '%d/%m/%Y'),
                        STR_TO_DATE(jc.date_of_request, '%d-%m-%Y')
                    ) <= STR_TO_DATE(?, '%Y-%m-%d')";
            $types .= "s";
            $params[] = $dateTo;
        }
        
        if ($withHuidOnly) {
            $sql .= " AND EXISTS (
                        SELECT 1 
                        FROM huid_data hd2 
                        WHERE hd2.job_no = jc.job_no AND hd2.weight > 0
                    )";
        }
        
        $sql .= " ORDER BY jc.id DESC LIMIT ?, ?";
        $types .= "ii";
        $params[] = $offset;
        $params[] = $limit;
        
        $stmt = $conn->prepare($sql);
        if (!$stmt) throw new Exception("Prepare failed: " . $conn->error);
        $stmt->bind_param($types, ...$params);
        
        if (!$stmt->execute()) {
            throw new Exception("Execute failed: " . $stmt->error);
        }
        
        $result = $stmt->get_result();
        $data = [];
        while ($row = $result->fetch_assoc()) {
            $data[] = $row;
        }
        $stmt->close();
        
        sendResponse('success', 'Fetched weight capture jobs', $data);
    }
    
    // === ACTION: Get Missing Job Numbers (Load Missing) ===
    elseif ($action === 'get_missing_job_numbers') {
        $firmId = $request['firm_id'] ?? '';
        
        if (empty($firmId)) {
            sendResponse('error', 'Missing firm_id');
        }

        $sql = "SELECT id, request_no, item, pcs, purity, weight
                FROM job_cards 
                WHERE firm_id = ? 
                AND (job_no IS NULL OR job_no = '' OR job_no = '0')
                ORDER BY request_no, id";
                
        $stmt = $conn->prepare($sql);
        if (!$stmt) throw new Exception("Prepare failed: " . $conn->error);
        $stmt->bind_param("s", $firmId);
        
        if (!$stmt->execute()) {
             throw new Exception("Execute failed: " . $stmt->error);
        }
        
        $result = $stmt->get_result();
        $data = [];
        while ($row = $result->fetch_assoc()) {
            $data[] = $row;
        }
        $stmt->close();
        sendResponse('success', 'Fetched missing job numbers', $data);
    }

    // === ACTION: Update Job Card (Single) ===
    elseif ($action === 'update_job_card') {
        $id = $request['id'] ?? '';
        $jobNo = $request['job_no'] ?? '';
        
        if (empty($id) || empty($jobNo)) {
            sendResponse('error', 'Missing id or job_no');
        }
        
        $sql = "UPDATE job_cards SET job_no = ? WHERE id = ?";
        $stmt = $conn->prepare($sql);
        if (!$stmt) throw new Exception("Prepare failed: " . $conn->error);
        
        $stmt->bind_param("si", $jobNo, $id);
        if (!$stmt->execute()) {
             throw new Exception("Execute failed: " . $stmt->error);
        }
        
        if ($stmt->affected_rows > 0) {
            sendResponse('success', 'Job updated successfully');
        } else {
            // Check if it was already updated
            sendResponse('success', 'No changes made (already updated?)');
        }
    }

    // === ACTION: Update Job Card By Request (All items in request to one job) ===
    elseif ($action === 'update_job_card_by_request') {
        $requestNo = $request['request_no'] ?? '';
        $jobNo = $request['job_no'] ?? '';
        $firmId = $request['firm_id'] ?? '';
        
        if (empty($requestNo) || empty($jobNo) || empty($firmId)) {
             sendResponse('error', 'Missing request_no, job_no, or firm_id');
        }
        
        $sql = "UPDATE job_cards SET job_no = ? WHERE request_no = ? AND firm_id = ? AND (job_no IS NULL OR job_no = '' OR job_no = '0')";
        $stmt = $conn->prepare($sql);
        if (!$stmt) throw new Exception("Prepare failed: " . $conn->error);
        
        $stmt->bind_param("sss", $jobNo, $requestNo, $firmId);
        if (!$stmt->execute()) {
             throw new Exception("Execute failed: " . $stmt->error);
        }
        
        sendResponse('success', 'Updated items by request', ['updated_rows' => $stmt->affected_rows]);
    }

    // === ACTION: Get Weights (huid_data) ===
    if ($action === 'get_weights') {
        $jobNumbers = $request['job_numbers'] ?? [];

        if (empty($jobNumbers)) {
            sendResponse('success', 'No job numbers provided', []);
        }

        // Create placeholders for IN clause (?,?,?)
        $placeholders = implode(',', array_fill(0, count($jobNumbers), '?'));
        // Type definition string (all strings)
        $types = str_repeat('s', count($jobNumbers));
        
        $sql = "SELECT job_no, tag_no, weight, huid_code 
                FROM huid_data 
                WHERE job_no IN ($placeholders) 
                AND weight > 0 
                ORDER BY job_no, serial_no";
                
        $stmt = $conn->prepare($sql);
        if (!$stmt) {
            throw new Exception("Prepare failed: " . $conn->error);
        }

        $stmt->bind_param($types, ...$jobNumbers);
        
        if (!$stmt->execute()) {
            throw new Exception("Execute failed: " . $stmt->error);
        }

        $result = $stmt->get_result();
        $weights = [];
        while ($row = $result->fetch_assoc()) {
            $weights[] = [
                'job_no' => $row['job_no'],
                'tag_no' => $row['tag_no'],
                'weight' => (float)$row['weight'],
                'huid_code' => $row['huid_code']
            ];
        }
        $stmt->close();
        
        sendResponse('success', 'Weights fetched successfully', $weights);
    }

    // === ACTION: Update HUID Codes (INSERT/UPDATE logic) ===
    elseif ($action === 'update_huid_codes') {
        $mappings = $request['mappings'] ?? [];
        $jobNo = $request['job_no'] ?? '';
        
        if (empty($mappings) || empty($jobNo)) {
            sendResponse('error', 'Missing mappings or job number');
        }
        
        $updatedCount = 0;
        
        // Prepare CHECK statement
        $checkSql = "SELECT id FROM huid_data WHERE job_no = ? AND tag_no = ?";
        $checkStmt = $conn->prepare($checkSql);

        // Prepare UPDATE statement
        $updateSql = "UPDATE huid_data SET huid_code = ?, weight = ?, updated_at = NOW() WHERE id = ?";
        $updateStmt = $conn->prepare($updateSql);
        
        // Prepare INSERT statement
        // Note: Using some defaults for required fields if needed
        $insertSql = "INSERT INTO huid_data (job_no, tag_no, huid_code, weight, updated_at, firm_id) VALUES (?, ?, ?, ?, NOW(), ?)";
        $insertStmt = $conn->prepare($insertSql);
        
        if (!$checkStmt || !$updateStmt || !$insertStmt) {
             throw new Exception("Prepare failed: " . $conn->error);
        }

        // Get firm_id from first job if possible, or mapping? 
        // We'll pass firm_id separately or query job_cards for it?
        // Let's query firm_id from job_cards first
        $firmId = 2; // Default
        $firmSql = "SELECT firm_id FROM job_cards WHERE job_no = ? LIMIT 1";
        $firmStmt = $conn->prepare($firmSql);
        if ($firmStmt) {
            $firmStmt->bind_param("s", $jobNo);
            $firmStmt->execute();
            $res = $firmStmt->get_result();
            if ($r = $res->fetch_assoc()) {
                $firmId = $r['firm_id'];
            }
            $firmStmt->close();
        }

        foreach ($mappings as $mapping) {
            $huidCode = $mapping['huid_code'];
            $tagNo = $mapping['tag_no'];
            $weight = isset($mapping['weight']) ? (float)$mapping['weight'] : 0.0;
            
            // Skip empty items if tag missing
            if (empty($tagNo)) continue;
            
            // Check if exists
            $checkStmt->bind_param("ss", $jobNo, $tagNo);
            $checkStmt->execute();
            $res = $checkStmt->get_result();
            
            if ($row = $res->fetch_assoc()) {
                // Update existing
                $id = $row['id'];
                $updateStmt->bind_param("sdi", $huidCode, $weight, $id);
                $updateStmt->execute();
                if ($updateStmt->affected_rows > 0) {
                    $updatedCount++;
                }
            } else {
                // Insert new
                $insertStmt->bind_param("sssdi", $jobNo, $tagNo, $huidCode, $weight, $firmId);
                $insertStmt->execute();
                if ($insertStmt->affected_rows > 0) {
                    $updatedCount++;
                }
            }
        }
        
        $checkStmt->close();
        $updateStmt->close();
        $insertStmt->close();
        
        echo json_encode([
            'status' => 'success',
            'message' => "Updated/Inserted $updatedCount HUID codes/weights",
            'updated_count' => $updatedCount
        ]);
        exit;
    }
    
    // === ACTION: Get Job Details for Delivery Voucher ===
    elseif ($action === 'get_job_details_for_voucher') {
        $firmId = $request['firm_id'] ?? '';
        $jobNumbers = $request['job_numbers'] ?? [];

        if (empty($firmId) || empty($jobNumbers)) {
            sendResponse('success', 'Missing firm_id or job_numbers', []);
        }

        // Create placeholders
        $placeholders = implode(',', array_fill(0, count($jobNumbers), '?'));
        $types = 's' . str_repeat('s', count($jobNumbers));
        $params = array_merge([$firmId], $jobNumbers);

        $sql = "SELECT job_no, id, item, weight, scrp_cornet_weight 
                FROM job_cards 
                WHERE firm_id = ? AND job_no IN ($placeholders)";

        $stmt = $conn->prepare($sql);
        if (!$stmt) {
             throw new Exception("Prepare failed: " . $conn->error);
        }
        
        $stmt->bind_param($types, ...$params);
        
        if (!$stmt->execute()) {
            throw new Exception("Execute failed: " . $stmt->error);
        }
        
        $result = $stmt->get_result();
        
        $jobs = [];
        while ($row = $result->fetch_assoc()) {
            $jobs[$row['job_no']] = [
                'id' => $row['id'],
                'item' => $row['item'],
                'weight' => (float)$row['weight'],
                'scrp_cornet_weight' => (float)$row['scrp_cornet_weight'],
                'scrap_weight' => (float)$row['scrp_cornet_weight'] // Alias for compatibility
            ];
        }
        $stmt->close();
        
        sendResponse('success', 'Job details fetched', $jobs);
    }
    
    // === ACTION: Get Job Details (PCS & Weight) ===
    elseif ($action === 'get_job_details') {
        $jobNumbers = $request['job_numbers'] ?? [];
        
        if (empty($jobNumbers)) {
            sendResponse('success', 'No job numbers provided', []);
        }
        
        $placeholders = implode(',', array_fill(0, count($jobNumbers), '?'));
        $types = str_repeat('s', count($jobNumbers));
        
        $sql = "SELECT job_no, pcs, weight, item FROM job_cards WHERE job_no IN ($placeholders)";
        
        $stmt = $conn->prepare($sql);
        if (!$stmt) {
             throw new Exception("Prepare failed: " . $conn->error);
        }
        $stmt->bind_param($types, ...$jobNumbers);
        if (!$stmt->execute()) {
            throw new Exception("Execute failed: " . $stmt->error);
        }
        $result = $stmt->get_result();
        $data = [];
        while ($row = $result->fetch_assoc()) {
            $data[] = [
                'job_no' => $row['job_no'],
                'pcs' => $row['pcs'],
                'weight' => $row['weight'],
                'item' => $row['item']
            ];
        }
        $stmt->close();
        sendResponse('success', 'Job details fetched successfully', $data);
    }
    
    // === ACTION: Check Connection ===
    elseif ($action === 'check_connection') {
        sendResponse('success', 'Connection successful');
    }
    
    // === ACTION: Save Request to Database ===
    elseif ($action === 'save_request_to_db') {
        $firmId = $request['firm_id'] ?? '';
        $requestNo = $request['request_no'] ?? '';
        $dateOfRequest = $request['date_of_request'] ?? '';
        $item = $request['item'] ?? '';
        $description = $request['description'] ?? '';
        $jobNo = $request['job_no'] ?? '';
        $status = $request['status'] ?? 'Created';

        if (empty($firmId) || empty($requestNo)) {
             sendResponse('error', 'Missing firm_id or request_no');
        }

        // First check if the request already exists
        $checkSql = "SELECT id FROM job_cards WHERE request_no = ? AND firm_id = ?";
        $checkStmt = $conn->prepare($checkSql);
        if (!$checkStmt) throw new Exception("Prepare check failed: " . $conn->error);
        $checkStmt->bind_param("ss", $requestNo, $firmId);
        $checkStmt->execute();
        $res = $checkStmt->get_result();
        $existingRows = $res->num_rows;
        $checkStmt->close();

        if ($existingRows > 0) {
            // SAFETY CHECK: If multiple rows exist for this request, it likely has multiple items
            // Do NOT use a bulk UPDATE as it would set all rows to the same item name
            // Instead, only update job_no (never item) to prevent data corruption
            if ($existingRows > 1) {
                // Multiple items in request - only update job_no, do NOT modify item names
                $sql = "UPDATE job_cards 
                        SET job_no = IF(job_no IS NULL OR job_no = '', ?, job_no),
                            status = IF(? != '', ?, status)
                        WHERE request_no = ? AND firm_id = ?
                        AND (job_no IS NULL OR job_no = '' OR job_no = '0')";
                
                $stmt = $conn->prepare($sql);
                if (!$stmt) throw new Exception("Prepare update (multi-item) failed: " . $conn->error);
                $stmt->bind_param("ssss", $jobNo, $status, $status, $requestNo, $firmId);
                if (!$stmt->execute()) {
                    throw new Exception("Execute failed: " . $stmt->error);
                }
                sendResponse('success', 'Request updated safely (multi-item detected - item names preserved)');
            } else {
                // Single item - safe to update all fields
                $sql = "UPDATE job_cards 
                        SET 
                            date_of_request = COALESCE(NULLIF(?, ''), date_of_request),
                            item = IF(item IS NULL OR item = '', ?, item),
                            description = IF(description IS NULL OR description = '', ?, description),
                            job_no = IF(job_no IS NULL OR job_no = '', ?, job_no),
                            status = IF(? != '', ?, status)
                        WHERE request_no = ? AND firm_id = ?";
                
                $stmt = $conn->prepare($sql);
                if (!$stmt) throw new Exception("Prepare update failed: " . $conn->error);
                $stmt->bind_param("ssssssss", $dateOfRequest, $item, $description, $jobNo, $status, $status, $requestNo, $firmId);
                if (!$stmt->execute()) {
                     throw new Exception("Execute failed: " . $stmt->error);
                }
                sendResponse('success', 'Request updated successfully');
            }
        } else {
             // Fallback: INSERT if no row exists
             $insertSql = "INSERT INTO job_cards (
                 firm_id, request_no, date_of_request, item, description, job_no, status, created_at
             ) VALUES (?, ?, ?, ?, ?, ?, ?, NOW())";
             
             $insertStmt = $conn->prepare($insertSql);
             if (!$insertStmt) {
                 throw new Exception("Prepare insert failed: " . $conn->error);
             }
             $insertStmt->bind_param("sssssss", $firmId, $requestNo, $dateOfRequest, $item, $description, $jobNo, $status);
             $insertStmt->execute();
             $insertStmt->close();
             
             sendResponse('success', 'Request inserted successfully');
        }
    }

    else {
        throw new Exception("Invalid action: $action");
    }

} catch (Exception $e) {
    http_response_code(500);
    echo json_encode([
        'status' => 'error', 
        'message' => $e->getMessage()
    ]);
}

$conn->close();
?>
