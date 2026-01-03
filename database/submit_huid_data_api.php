<?php
header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: POST, GET, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type');

// Handle preflight OPTIONS request
if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    http_response_code(200);
    exit();
}

// Database connection
$host = 'localhost';
$db = 'u176143338_hallmarkProver';
$user = 'u176143338_hallmarkProver';
$pass = 'Rontik10@';

$conn = new mysqli($host, $user, $pass, $db);

if ($conn->connect_error) {
    http_response_code(500);
    echo json_encode(['error' => 'Database connection failed']);
    exit;
}

// Get JSON input
$input = file_get_contents('php://input');
$data = json_decode($input, true);

if (!$data) {
    http_response_code(400);
    echo json_encode(['error' => 'Invalid JSON data']);
    exit;
}

$action = $data['action'] ?? '';

if ($action === 'submit_huid_data') {
    $huid_data = $data['data'] ?? [];
    
    if (empty($huid_data)) {
        echo json_encode(['error' => 'No HUID data provided']);
        exit;
    }
    
    $success_count = 0;
    $error_count = 0;
    $errors = [];
    
    // Start transaction
    $conn->begin_transaction();
    
    try {
        foreach ($huid_data as $record) {
            // Validate required fields
            $required_fields = ['job_no', 'huid_code', 'weight', 'material', 'item'];
            $missing_fields = [];
            
            foreach ($required_fields as $field) {
                if (empty($record[$field])) {
                    $missing_fields[] = $field;
                }
            }
            
            if (!empty($missing_fields)) {
                $errors[] = "Missing required fields for HUID {$record['huid_code']}: " . implode(', ', $missing_fields);
                $error_count++;
                continue;
            }
            
            // Check if record already exists (prevent duplicates by huid_code)
            $check_sql = "SELECT id FROM huid_data WHERE huid_code = ?";
            $check_stmt = $conn->prepare($check_sql);
            $check_stmt->bind_param("s", $record['huid_code']);
            $check_stmt->execute();
            $result = $check_stmt->get_result();
            
            if ($result->num_rows > 0) {
                // Update existing record
                $update_sql = "UPDATE huid_data SET 
                    weight = ?, 
                    material = ?, 
                    item = ?, 
                    pair_id = ?,
                    date_added = ?,
                    remarks = ?
                    WHERE huid_code = ?";
                
                $update_stmt = $conn->prepare($update_sql);
                $update_stmt->bind_param("dsssss", 
                    $record['weight'],
                    $record['material'],
                    $record['item'],
                    $record['pair_id'],
                    $record['date_added'],
                    $record['remarks'],
                    $record['huid_code']
                );
                
                if ($update_stmt->execute()) {
                    $success_count++;
                } else {
                    $errors[] = "Failed to update HUID {$record['huid_code']}: " . $conn->error;
                    $error_count++;
                }
                $update_stmt->close();
            } else {
                // Insert new record
                $insert_sql = "INSERT INTO huid_data (
                    job_id, job_no, request_no, purity, serial_no, tag_no, 
                    material, item, huid_code, weight, date_added, image_path, 
                    pair_id, firm_id, party_id, remarks
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)";
                
                $insert_stmt = $conn->prepare($insert_sql);
                $insert_stmt->bind_param("sssssssssdssssss",
                    $record['job_id'],
                    $record['job_no'],
                    $record['request_no'],
                    $record['purity'],
                    $record['serial_no'],
                    $record['tag_no'],
                    $record['material'],
                    $record['item'],
                    $record['huid_code'],
                    $record['weight'],
                    $record['date_added'],
                    $record['image_path'],
                    $record['pair_id'],  // This will store the huid_code as requested
                    $record['firm_id'],
                    $record['party_id'],
                    $record['remarks']
                );
                
                if ($insert_stmt->execute()) {
                    $success_count++;
                } else {
                    $errors[] = "Failed to insert HUID {$record['huid_code']}: " . $conn->error;
                    $error_count++;
                }
                $insert_stmt->close();
            }
            
            $check_stmt->close();
        }
        
        // Commit transaction
        $conn->commit();
        
        $response = [
            'success' => true,
            'message' => 'HUID data processed successfully',
            'summary' => [
                'total_records' => count($huid_data),
                'success_count' => $success_count,
                'error_count' => $error_count
            ]
        ];
        
        if (!empty($errors)) {
            $response['errors'] = $errors;
        }
        
        echo json_encode($response, JSON_PRETTY_PRINT);
        
    } catch (Exception $e) {
        // Rollback transaction on error
        $conn->rollback();
        
        http_response_code(500);
        echo json_encode([
            'success' => false,
            'error' => 'Transaction failed: ' . $e->getMessage()
        ]);
    }
    
} elseif ($action === 'get_huid_data') {
    // Get HUID data for a specific job
    $job_no = $data['job_no'] ?? '';
    
    if (empty($job_no)) {
        echo json_encode(['error' => 'Job number required']);
        exit;
    }
    
    $sql = "SELECT * FROM huid_data WHERE job_no = ? ORDER BY date_added DESC";
    $stmt = $conn->prepare($sql);
    $stmt->bind_param("s", $job_no);
    $stmt->execute();
    $result = $stmt->get_result();
    
    $huid_data = [];
    while ($row = $result->fetch_assoc()) {
        $huid_data[] = $row;
    }
    
    echo json_encode([
        'success' => true,
        'data' => $huid_data,
        'count' => count($huid_data)
    ], JSON_PRETTY_PRINT);
    
    $stmt->close();
    
} else {
    http_response_code(400);
    echo json_encode(['error' => 'Invalid action']);
}

$conn->close();
?>
