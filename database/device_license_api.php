<?php
/**
 * Device License API for MANAK Automation
 * Handles device registration and verification
 * 
 * Server: https://hallmarkpro.prosenjittechhub.com/admin/
 * Database: Your database with device_licenses table
 */

header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: POST, GET, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type');

// Database configuration
$db_host = 'localhost';
$db_name = 'your_database_name';
$db_user = 'your_db_username';
$db_pass = 'your_db_password';

try {
    $pdo = new PDO("mysql:host=$db_host;dbname=$db_name;charset=utf8", $db_user, $db_pass);
    $pdo->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);
} catch(PDOException $e) {
    http_response_code(500);
    echo json_encode(['success' => false, 'message' => 'Database connection failed']);
    exit;
}

// Get request data
$input = json_decode(file_get_contents('php://input'), true);
if (!$input) {
    $input = $_POST;
}

$action = $input['action'] ?? '';
$device_id = $input['device_id'] ?? '';
$user_id = $input['user_id'] ?? '';
$timestamp = $input['timestamp'] ?? '';

// Validate required fields
if (empty($action) || empty($device_id)) {
    http_response_code(400);
    echo json_encode(['success' => false, 'message' => 'Missing required parameters']);
    exit;
}

switch ($action) {
    case 'verify_device':
        verifyDevice($pdo, $device_id, $user_id);
        break;
        
    case 'register_device':
        registerDevice($pdo, $device_id, $user_id);
        break;
        
    case 'revoke_device':
        revokeDevice($pdo, $device_id, $user_id);
        break;
        
    case 'get_device_status':
        getDeviceStatus($pdo, $device_id);
        break;
        
    case 'register_trial':
        registerTrial($pdo, $input);
        break;
        
    case 'check_trial':
        checkTrial($pdo, $input);
        break;
        
    default:
        http_response_code(400);
        echo json_encode(['success' => false, 'message' => 'Invalid action']);
        break;
}

function verifyDevice($pdo, $device_id, $user_id) {
    try {
        // Check if device is registered and active
        $stmt = $pdo->prepare("
            SELECT * FROM device_licenses 
            WHERE device_id = ? AND user_id = ? AND status = 'active'
        ");
        $stmt->execute([$device_id, $user_id]);
        $device = $stmt->fetch(PDO::FETCH_ASSOC);
        
        if ($device) {
            // Check if license is expired
            if (!empty($device['expires_at']) && strtotime($device['expires_at']) < time()) {
                echo json_encode([
                    'success' => false, 
                    'message' => 'Device license has expired',
                    'device_id' => $device_id
                ]);
                return;
            }
            
            // Update last_verified timestamp
            $update_stmt = $pdo->prepare("
                UPDATE device_licenses 
                SET last_verified = NOW() 
                WHERE device_id = ? AND user_id = ?
            ");
            $update_stmt->execute([$device_id, $user_id]);
            
            echo json_encode([
                'success' => true,
                'message' => 'Device authorized',
                'device_id' => $device_id,
                'user_id' => $user_id,
                'expires_at' => $device['expires_at'],
                'license_type' => $device['license_type'],
                'firm_id' => $device['firm_id']
            ]);
        } else {
            echo json_encode([
                'success' => false,
                'message' => 'Device not registered or inactive',
                'device_id' => $device_id
            ]);
        }
    } catch (Exception $e) {
        http_response_code(500);
        echo json_encode(['success' => false, 'message' => 'Database error: ' . $e->getMessage()]);
    }
}

function registerDevice($pdo, $device_id, $user_id) {
    try {
        // Check if device already exists
        $stmt = $pdo->prepare("SELECT * FROM device_licenses WHERE device_id = ?");
        $stmt->execute([$device_id]);
        $existing = $stmt->fetch(PDO::FETCH_ASSOC);
        
        if ($existing) {
            echo json_encode([
                'success' => false,
                'message' => 'Device already registered'
            ]);
            return;
        }
        
        // Register new device
        $stmt = $pdo->prepare("
            INSERT INTO device_licenses (device_id, user_id, status, created_at, expires_at, license_type)
            VALUES (?, ?, 'active', NOW(), DATE_ADD(NOW(), INTERVAL 1 YEAR), 'standard')
        ");
        $stmt->execute([$device_id, $user_id]);
        
        echo json_encode([
            'success' => true,
            'message' => 'Device registered successfully',
            'device_id' => $device_id,
            'user_id' => $user_id
        ]);
    } catch (Exception $e) {
        http_response_code(500);
        echo json_encode(['success' => false, 'message' => 'Database error: ' . $e->getMessage()]);
    }
}

function revokeDevice($pdo, $device_id, $user_id) {
    try {
        $stmt = $pdo->prepare("
            UPDATE device_licenses 
            SET status = 'revoked', revoked_at = NOW() 
            WHERE device_id = ? AND user_id = ?
        ");
        $stmt->execute([$device_id, $user_id]);
        
        if ($stmt->rowCount() > 0) {
            echo json_encode([
                'success' => true,
                'message' => 'Device revoked successfully'
            ]);
        } else {
            echo json_encode([
                'success' => false,
                'message' => 'Device not found'
            ]);
        }
    } catch (Exception $e) {
        http_response_code(500);
        echo json_encode(['success' => false, 'message' => 'Database error: ' . $e->getMessage()]);
    }
}

function getDeviceStatus($pdo, $device_id) {
    try {
        // First check device license
        $stmt = $pdo->prepare("
            SELECT * FROM device_licenses 
            WHERE device_id = ?
        ");
        $stmt->execute([$device_id]);
        $device = $stmt->fetch(PDO::FETCH_ASSOC);
        
        if ($device) {
            echo json_encode([
                'success' => true,
                'device' => $device
            ]);
            return;
        }
        
        // If no license, check trial
        $stmt = $pdo->prepare("
            SELECT * FROM device_trials 
            WHERE device_id = ?
        ");
        $stmt->execute([$device_id]);
        $trial = $stmt->fetch(PDO::FETCH_ASSOC);
        
        if ($trial) {
            echo json_encode([
                'success' => true,
                'trial' => $trial
            ]);
        } else {
            echo json_encode([
                'success' => false,
                'message' => 'Device not found'
            ]);
        }
    } catch (Exception $e) {
        http_response_code(500);
        echo json_encode(['success' => false, 'message' => 'Database error: ' . $e->getMessage()]);
    }
}

function registerTrial($pdo, $input) {
    try {
        $device_id = $input['device_id'];
        $mac_address = $input['mac_address'];
        $portal_username = $input['portal_username'] ?? null;
        
        if (empty($device_id) || empty($mac_address)) {
            echo json_encode(['success' => false, 'message' => 'Missing device information']);
            return;
        }
        
        // Check if device already has a license
        $stmt = $pdo->prepare("SELECT * FROM device_licenses WHERE device_id = ? OR mac_address = ?");
        $stmt->execute([$device_id, $mac_address]);
        if ($stmt->fetch()) {
            echo json_encode(['success' => false, 'message' => 'Device already licensed']);
            return;
        }
        
        // Check if device already has a trial
        $stmt = $pdo->prepare("SELECT * FROM device_trials WHERE device_id = ? OR mac_address = ?");
        $stmt->execute([$device_id, $mac_address]);
        if ($stmt->fetch()) {
            echo json_encode(['success' => false, 'message' => 'Trial already exists for this device']);
            return;
        }
        
        // Register new trial
        $start_date = date('Y-m-d H:i:s');
        $expiry_date = date('Y-m-d H:i:s', strtotime('+3 days')); // 3-day trial
        
        $stmt = $pdo->prepare("
            INSERT INTO device_trials (
                device_id,
                mac_address,
                portal_username,
                start_date,
                expiry_date,
                status
            ) VALUES (?, ?, ?, ?, ?, 'active')
        ");
        
        $stmt->execute([
            $device_id,
            $mac_address,
            $portal_username,
            $start_date,
            $expiry_date
        ]);
        
        echo json_encode([
            'success' => true,
            'message' => 'Trial registered successfully',
            'trial_info' => [
                'device_id' => $device_id,
                'mac_address' => $mac_address,
                'start_date' => $start_date,
                'expiry_date' => $expiry_date
            ]
        ]);
        
    } catch (Exception $e) {
        http_response_code(500);
        echo json_encode(['success' => false, 'message' => 'Database error: ' . $e->getMessage()]);
    }
}

function checkTrial($pdo, $input) {
    try {
        $device_id = $input['device_id'];
        $mac_address = $input['mac_address'];
        
        if (empty($device_id) || empty($mac_address)) {
            echo json_encode(['success' => false, 'message' => 'Missing device information']);
            return;
        }
        
        // Check if device has a valid license first
        $stmt = $pdo->prepare("SELECT * FROM device_licenses WHERE device_id = ? AND status = 'active'");
        $stmt->execute([$device_id]);
        if ($stmt->fetch()) {
            echo json_encode(['success' => true, 'message' => 'Device is licensed']);
            return;
        }
        
        // Check trial status
        $stmt = $pdo->prepare("
            SELECT * FROM device_trials 
            WHERE device_id = ? 
            AND mac_address = ? 
            AND status = 'active'
        ");
        $stmt->execute([$device_id, $mac_address]);
        $trial = $stmt->fetch(PDO::FETCH_ASSOC);
        
        if (!$trial) {
            echo json_encode(['success' => false, 'message' => 'No active trial found']);
            return;
        }
        
        // Check if trial has expired
        if (strtotime($trial['expiry_date']) < time()) {
            // Update trial status to expired
            $stmt = $pdo->prepare("
                UPDATE device_trials 
                SET status = 'expired' 
                WHERE device_id = ?
            ");
            $stmt->execute([$device_id]);
            
            echo json_encode(['success' => false, 'message' => 'Trial has expired']);
            return;
        }
        
        // Calculate remaining days
        $remaining_days = ceil((strtotime($trial['expiry_date']) - time()) / (60 * 60 * 24));
        
        echo json_encode([
            'success' => true,
            'message' => 'Trial is active',
            'trial_info' => [
                'device_id' => $trial['device_id'],
                'mac_address' => $trial['mac_address'],
                'start_date' => $trial['start_date'],
                'expiry_date' => $trial['expiry_date'],
                'remaining_days' => $remaining_days
            ]
        ]);
        
    } catch (Exception $e) {
        http_response_code(500);
        echo json_encode(['success' => false, 'message' => 'Database error: ' . $e->getMessage()]);
    }
}
?> 