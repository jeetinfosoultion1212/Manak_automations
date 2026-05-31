<?php
// save_job_api.php
// Handles saving job cards and HUID data
// Actions: 'save_job', 'save_jobs' (batch), 'save_huids'
//
// One MANAK request_no may have MULTIPLE items (Earings, Nosepin, etc.).
// Duplicate = same firm + request_no + item + pcs + weight (+ purity when set).

header('Content-Type: application/json');
header("Access-Control-Allow-Origin: *");
header("Access-Control-Allow-Headers: Content-Type");

$servername = "localhost";
$username = "u176143338_hallmarkProver";
$password = "Rontik10@";
$dbname = "u176143338_hallmarkProver";

$conn = new mysqli($servername, $username, $password, $dbname);

if ($conn->connect_error) {
    http_response_code(500);
    die(json_encode(["success" => false, "message" => "Connection failed: " . $conn->connect_error]));
}

$data = json_decode(file_get_contents("php://input"), true);

if (!isset($data['action'])) {
    echo json_encode(["success" => false, "message" => "Action required"]);
    exit;
}

$action = $data['action'];
$firm_id = isset($data['firm_id']) ? intval($data['firm_id']) : 2;

/**
 * True duplicate row (same item line), NOT merely same request number.
 */
function job_row_already_exists($conn, $firm_id, $job)
{
    $request_no = trim($job['request_no'] ?? '');
    if ($request_no === '') {
        return false;
    }

    $item = trim($job['item'] ?? '');
    $pcs = intval($job['pcs'] ?? 0);
    $weight = round(floatval($job['weight'] ?? 0), 3);
    $purity = trim($job['purity'] ?? '');

    if ($purity !== '') {
        $sql = "SELECT id FROM job_cards
                WHERE firm_id = ? AND request_no = ? AND item = ?
                  AND pcs = ? AND ROUND(weight, 3) = ?
                  AND COALESCE(purity, '') = ?
                LIMIT 1";
        $stmt = $conn->prepare($sql);
        if (!$stmt) {
            return false;
        }
        $stmt->bind_param("issids", $firm_id, $request_no, $item, $pcs, $weight, $purity);
    } else {
        $sql = "SELECT id FROM job_cards
                WHERE firm_id = ? AND request_no = ? AND item = ?
                  AND pcs = ? AND ROUND(weight, 3) = ?
                LIMIT 1";
        $stmt = $conn->prepare($sql);
        if (!$stmt) {
            return false;
        }
        $stmt->bind_param("issid", $firm_id, $request_no, $item, $pcs, $weight);
    }

    $stmt->execute();
    $res = $stmt->get_result();
    $exists = $res && $res->num_rows > 0;
    $stmt->close();
    return $exists;
}

function job_no_already_exists($conn, $firm_id, $job_no)
{
    $job_no = trim($job_no ?? '');
    if ($job_no === '') {
        return false;
    }
    $stmt = $conn->prepare("SELECT id FROM job_cards WHERE job_no = ? AND firm_id = ? LIMIT 1");
    if (!$stmt) {
        return false;
    }
    $stmt->bind_param("si", $job_no, $firm_id);
    $stmt->execute();
    $res = $stmt->get_result();
    $exists = $res && $res->num_rows > 0;
    $stmt->close();
    return $exists;
}

/**
 * Insert one job_cards row. Returns associative result for JSON.
 */
function save_one_job_card($conn, $firm_id, $job)
{
    if (!$job || empty($job['request_no'])) {
        return ["success" => false, "saved" => false, "message" => "Job data / request_no required"];
    }

    $job_no = trim($job['job_no'] ?? '');
    if ($job_no !== '' && job_no_already_exists($conn, $firm_id, $job_no)) {
        return [
            "success" => true,
            "saved" => false,
            "message" => "Job no already exists: " . $job_no,
            "item" => $job['item'] ?? '',
        ];
    }

    if (job_row_already_exists($conn, $firm_id, $job)) {
        return [
            "success" => true,
            "saved" => false,
            "message" => "Duplicate row for Request #" . $job['request_no']
                . " (same item/pcs/weight/purity)",
            "item" => $job['item'] ?? '',
        ];
    }

    $date_of_request = $job['date_of_request'] ?? date('Y-m-d');
    $licence_no = $job['licence_no'] ?? '';
    $request_no = $job['request_no'];
    $item = $job['item'] ?? '';
    $pcs = intval($job['pcs'] ?? 0);
    $weight = floatval($job['weight'] ?? 0);
    $huid_pcs = intval($job['huid_pcs'] ?? $pcs);
    $bill_no = $job['bill_no'] ?? null;
    $is_billed = intval($job['is_billed'] ?? 0);
    $status = $job['status'] ?? 'XRF';
    $cornet_weight = floatval($job['cornet_weight'] ?? 0);
    $scrp_cornet_weight = floatval($job['scrp_cornet_weight'] ?? 0);
    $material_type = $job['material_type'] ?? 'Gold';
    $purity = $job['purity'] ?? null;
    $created_at = $job['created_at'] ?? date('Y-m-d H:i:s');

    if ($job_no === '') {
        $job_no = '';
    }
    if ($bill_no === null) {
        $bill_no = '';
    }
    if ($purity === null) {
        $purity = '';
    }

    $sql = "INSERT INTO job_cards (
                firm_id, date_of_request, licence_no, request_no, job_no,
                item, pcs, weight, huid_pcs, bill_no, is_billed, status,
                cornet_weight, scrp_cornet_weight, material_type, purity, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)";

    $stmt = $conn->prepare($sql);
    if (!$stmt) {
        return ["success" => false, "saved" => false, "message" => "Prepare failed: " . $conn->error];
    }

    $stmt->bind_param(
        "isssssidissiddsss",
        $firm_id,
        $date_of_request,
        $licence_no,
        $request_no,
        $job_no,
        $item,
        $pcs,
        $weight,
        $huid_pcs,
        $bill_no,
        $is_billed,
        $status,
        $cornet_weight,
        $scrp_cornet_weight,
        $material_type,
        $purity,
        $created_at
    );

    if ($stmt->execute()) {
        $id = $stmt->insert_id;
        $stmt->close();
        return [
            "success" => true,
            "saved" => true,
            "message" => "Job saved successfully",
            "id" => $id,
            "item" => $item,
            "request_no" => $request_no,
        ];
    }

    $err = $stmt->error;
    $stmt->close();
    return ["success" => false, "saved" => false, "message" => "Error saving job: " . $err];
}

if ($action === 'save_job') {
    $job = $data['job'] ?? null;
    echo json_encode(save_one_job_card($conn, $firm_id, $job));

} elseif ($action === 'save_jobs') {
    $jobs = $data['jobs'] ?? [];
    if (!is_array($jobs) || count($jobs) === 0) {
        echo json_encode(["success" => false, "message" => "jobs array required"]);
        exit;
    }

    $results = [];
    $saved_count = 0;
    foreach ($jobs as $job) {
        $r = save_one_job_card($conn, $firm_id, $job);
        $results[] = $r;
        if (!empty($r['saved'])) {
            $saved_count++;
        }
    }

    echo json_encode([
        "success" => true,
        "message" => "Batch complete: $saved_count / " . count($jobs) . " saved",
        "saved_count" => $saved_count,
        "total" => count($jobs),
        "results" => $results,
    ]);

} elseif ($action === 'save_huids') {
    $job_no = $conn->real_escape_string($data['job_no']);
    $huid_list = $data['huid_list'];

    if (empty($huid_list)) {
        echo json_encode(["success" => true, "message" => "No HUIDs to save"]);
        exit;
    }

    $saved_count = 0;
    $errors = [];

    foreach ($huid_list as $huid_data) {
        $huid_code = $conn->real_escape_string($huid_data['huid']);
        $item = $conn->real_escape_string($huid_data['item_category']);
        $weight = floatval($huid_data['weight']);
        $serial_no = $conn->real_escape_string($huid_data['serial_no']);
        $date_added = date('Y-m-d H:i:s');

        $sql = "INSERT INTO huid_data (
                    firm_id, job_no, huid_code, item, weight, serial_no, date_added
                ) VALUES (
                    $firm_id, '$job_no', '$huid_code', '$item', $weight, '$serial_no', '$date_added'
                )";

        if ($conn->query($sql) === TRUE) {
            $saved_count++;
        } else {
            $errors[] = "Failed HUID $huid_code: " . $conn->error;
        }
    }

    echo json_encode([
        "success" => true,
        "saved_count" => $saved_count,
        "total" => count($huid_list),
        "errors" => $errors,
    ]);

} else {
    echo json_encode(["success" => false, "message" => "Invalid action"]);
}

$conn->close();
