<?php
// check_jobs_api.php
// Checks if job numbers exist in the database
// Expects POST request with JSON payload: {"job_numbers": ["123", "456"], "firm_id": 1}

header('Content-Type: application/json');
header("Access-Control-Allow-Origin: *");
header("Access-Control-Allow-Headers: Content-Type");

// Database configuration
// Replace with your actual database connection details if different
$servername = "localhost";
$username = "u176143338_hallmarkProver";
$password = "Rontik10@";
$dbname = "u176143338_hallmarkProver";

// Create connection
$conn = new mysqli($servername, $username, $password, $dbname);

// Check connection
if ($conn->connect_error) {
    http_response_code(500);
    die(json_encode(["success" => false, "message" => "Connection failed: " . $conn->connect_error]));
}

// Get POST data
$data = json_decode(file_get_contents("php://input"), true);

if (!isset($data['job_numbers']) || !is_array($data['job_numbers'])) {
    echo json_encode(["success" => false, "message" => "Invalid input. 'job_numbers' array required."]);
    exit;
}

$job_numbers = $data['job_numbers'];
$firm_id = isset($data['firm_id']) ? intval($data['firm_id']) : 2; // Default firm_id

if (empty($job_numbers)) {
    echo json_encode(["success" => true, "existing_jobs" => []]);
    exit;
}

// Sanitize and prepare list for IN clause
$escaped_jobs = array_map(function($job) use ($conn) {
    return "'" . $conn->real_escape_string($job) . "'";
}, $job_numbers);

$jobs_string = implode(",", $escaped_jobs);

$sql = "SELECT job_no FROM job_cards WHERE firm_id = $firm_id AND job_no IN ($jobs_string)";
$result = $conn->query($sql);

$existing_jobs = [];
if ($result && $result->num_rows > 0) {
    while($row = $result->fetch_assoc()) {
        $existing_jobs[] = $row['job_no'];
    }
}

echo json_encode(["success" => true, "existing_jobs" => $existing_jobs]);

$conn->close();
?>
