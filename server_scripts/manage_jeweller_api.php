<?php
// manage_jeweller_api.php
// Handles checking and creating jewellers
// Actions: 'check' or 'create'

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
        echo json_encode(["success" => false, "message" => "Fatal Error: " . $error['message'] . " on line " . $error['line']]);
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
    die(json_encode(["success" => false, "message" => "Connection failed: " . $conn->connect_error]));
}

// Set charset to utf8mb4 to handle all characters
$conn->set_charset("utf8mb4");

// Get POST data
$data = json_decode(file_get_contents("php://input"), true);

if (!isset($data['action'])) {
    echo json_encode(["success" => false, "message" => "Action required"]);
    exit;
}

$action = $data['action'];
$firm_id = isset($data['firm_id']) ? intval($data['firm_id']) : 2;
// Ensure string type for real_escape_string to avoid TypeError in newer PHP versions
$licence_no = isset($data['licence_no']) ? $conn->real_escape_string((string)$data['licence_no']) : '';

if ($action === 'check') {
    if (empty($licence_no)) {
        echo json_encode(["success" => false, "message" => "License number required"]);
        exit;
    }
    
    $sql = "SELECT id, Jewellers_Name as name FROM jewellers WHERE licence_no = '$licence_no' AND firm_id = $firm_id";
    $result = $conn->query($sql);
    
    if ($result && $result->num_rows > 0) {
        $row = $result->fetch_assoc();
        
        // Ensure data is UTF-8 encoded for json_encode
        if (isset($row['name']) && $row['name']) {
             $row['name'] = mb_convert_encoding($row['name'], 'UTF-8', 'UTF-8');
        }
        
        // Safe json encode
        $json = json_encode(["success" => true, "exists" => true, "jeweller" => $row], JSON_INVALID_UTF8_SUBSTITUTE);
        if ($json === false) {
             echo json_encode(["success" => true, "exists" => true, "jeweller" => ["id" => $row['id'], "name" => "Encoded Name Error"]]);
        } else {
             echo $json;
        }
    } else {
        echo json_encode(["success" => true, "exists" => false]);
    }
    
} elseif ($action === 'create') {
    $name = isset($data['name']) ? $conn->real_escape_string((string)$data['name']) : '';
    $address = isset($data['address']) ? $conn->real_escape_string((string)$data['address']) : '';
    $city = isset($data['city']) ? $conn->real_escape_string((string)$data['city']) : '';
    $state = isset($data['state']) ? $conn->real_escape_string((string)$data['state']) : '';
    $contact_no = isset($data['contact_no']) ? $conn->real_escape_string((string)$data['contact_no']) : '';
    $gst = isset($data['gst']) ? $conn->real_escape_string((string)$data['gst']) : '';
    $pan = isset($data['pan']) ? $conn->real_escape_string((string)$data['pan']) : '';
    
    if (empty($licence_no) || empty($name)) {
        echo json_encode(["success" => false, "message" => "License number and Name required"]);
        exit;
    }
    
    // Check if exists first
    $check_sql = "SELECT id FROM jewellers WHERE licence_no = '$licence_no' AND firm_id = $firm_id";
    $check_result = $conn->query($check_sql);
    
    if ($check_result && $check_result->num_rows > 0) {
        echo json_encode(["success" => true, "message" => "Jeweller already exists", "created" => false]);
        exit;
    }
    
    $created_at = date('Y-m-d H:i:s');
    
    // Updated column names based on schema: Jewellers_Name, Address1, Contact_no, GST, PAN
    $sql = "INSERT INTO jewellers (firm_id, licence_no, Jewellers_Name, Address1, City, State, Contact_no, GST, PAN, created_at) 
            VALUES ($firm_id, '$licence_no', '$name', '$address', '$city', '$state', '$contact_no', '$gst', '$pan', '$created_at')";
            
    if ($conn->query($sql) === TRUE) {
        echo json_encode(["success" => true, "message" => "Jeweller created successfully", "created" => true, "id" => $conn->insert_id]);
    } else {
        echo json_encode(["success" => false, "message" => "Error creating jeweller: " . $conn->error]);
    }
} else {
    echo json_encode(["success" => false, "message" => "Invalid action"]);
}

$conn->close();
?>
