<?php
// bill_import_api.php
// Integrated Bill Import - Saves matched bills following the complete accounting workflow
// Actions: 'save_matched_bill' (creates transaction entries and updates related tables)

header('Content-Type: application/json');
header("Access-Control-Allow-Origin: *");
header("Access-Control-Allow-Headers: Content-Type");

// Enable error logging but disable display to prevent invalid JSON
ini_set('display_errors', 0);
ini_set('log_errors', 1);
error_reporting(E_ALL);

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

// Set charset
$conn->set_charset("utf8mb4");

// Get POST data
$data = json_decode(file_get_contents("php://input"), true);

if (!isset($data['action'])) {
    echo json_encode(["success" => false, "message" => "Action required"]);
    exit;
}

$action = $data['action'];
$firm_id = isset($data['firm_id']) ? intval($data['firm_id']) : 1;

if ($action === 'save_matched_bill') {
    // Save Matched Bill-Job Pair following complete accounting workflow from bill_Save_method.md
    
    // Extract and sanitize variables - ALL FIELDS from bill_Save_method.md
    $job_id = isset($data['job_id']) ? intval($data['job_id']) : 0;
    $job_no = $conn->real_escape_string($data['job_no'] ?? '');
    $request_no = $conn->real_escape_string($data['request_no'] ?? '');
    $bill_number = $conn->real_escape_string($data['bill_number'] ?? '');
    $bill_date = $conn->real_escape_string($data['bill_date'] ?? date('Y-m-d'));
    $invoice_number = $conn->real_escape_string($data['invoice_number'] ?? '');
    $licence_no = $conn->real_escape_string($data['licence_no'] ?? '');
    $pcs = intval($data['pcs'] ?? 0);
    
    // Amount fields
    $base_amount = floatval($data['base_amount'] ?? $data['amount'] ?? 0);
    $amount = floatval($data['amount'] ?? 0);
    $cgst = floatval($data['cgst'] ?? 0);
    $sgst = floatval($data['sgst'] ?? 0);
    $igst = floatval($data['igst'] ?? 0);
    $gst_amount = floatval($data['gst_amount'] ?? ($cgst + $sgst + $igst));
    $gst_rate = floatval($data['gst_rate'] ?? 18.00);
    $total_amount = floatval($data['total_amount'] ?? 0);
    $round_off = floatval($data['round_off'] ?? 0);
    
    // Payment fields
    $confidence = floatval($data['confidence'] ?? 0);
    $payment_status = $conn->real_escape_string($data['payment_status'] ?? 'Unpaid');
    $payment_mode = $conn->real_escape_string($data['payment_mode'] ?? 'Bank');
    $paid_amount = floatval($data['paid_amount'] ?? 0);
    $received_amount = floatval($data['received_amount'] ?? 0);
    $payment_date = isset($data['payment_date']) ? $conn->real_escape_string($data['payment_date']) : NULL;
    
    // Weight fields
    $scrap_weight = floatval($data['scrap_weight'] ?? 0);
    $button_weight = floatval($data['button_weight'] ?? 0);
    $cornent_weight = floatval($data['cornent_weight'] ?? 0);
    $reminents_weight = floatval($data['reminents_weight'] ?? 0);
    
    // Other fields
    $narration = $conn->real_escape_string($data['narration'] ?? '');
    $voucher_id = $conn->real_escape_string($data['voucher_id'] ?? '');
    $is_jobs_wise = intval($data['is_jobs_wise'] ?? 1);
    $billing_type = $conn->real_escape_string($data['billing_type'] ?? 'full');
    $excluded_job_ids = $conn->real_escape_string($data['excluded_job_ids'] ?? '');
    $refer_party_id = isset($data['refer_party_id']) ? intval($data['refer_party_id']) : NULL;
    
    // Validation
    if (empty($bill_number) && empty($invoice_number)) {
        echo json_encode(["success" => false, "message" => "Bill number or invoice number is required"]);
        exit;
    }
    
    if (empty($job_no)) {
        echo json_encode(["success" => false, "message" => "Job number is required"]);
        exit;
    }
    
    try {
        // Start transaction
        $conn->begin_transaction();
        
        // 1. Check if bill already exists in transactions
        $check_sql = "
            SELECT id FROM transactions 
            WHERE firm_id = $firm_id 
              AND bill_no = '$bill_number'
            LIMIT 1
        ";
        $result = $conn->query($check_sql);
        
        if ($result && $result->num_rows > 0) {
            $conn->rollback();
            echo json_encode([
                "success" => true, 
                "message" => "Bill already exists",
                "saved" => false
            ]);
            exit;
        }
        
        // 2. INSERT into transactions table (PRIMARY TABLE)
        $created_at = date('Y-m-d H:i:s');
        if (empty($narration)) {
            $narration = "Matched bill {$bill_number} for Job {$job_no} (Confidence: {$confidence}%)";
        }
        if (empty($voucher_id)) {
            $voucher_id = "VCH/" . date('Y/m') . "/" . str_pad($firm_id, 3, '0', STR_PAD_LEFT) . "/" . str_pad(rand(1, 9999), 4, '0', STR_PAD_LEFT);
        }
        
        // Determine payment date if payment was received
        if ($received_amount > 0 && is_null($payment_date)) {
            $payment_date = $bill_date;
        }
        
        $insert_transactions = "
            INSERT INTO transactions (
                bill_no, firm_id, request_no, licence_no, 
                base_amount, total_amount,
                gst_amount, cgst_amount, sgst_amount, igst_amount, gst_rate,
                payment_status, payment_mode, paid_amount, received_amount, payment_date,
                scrap_weight, button_weight, cornent_weight, reminents_weight,
                narration, voucher_id, is_jobs_wise, billing_type, excluded_job_ids,
                round_off, date, created_at, updated_at, refer_party_id
            ) VALUES (
                '$bill_number', $firm_id, '$request_no', '$licence_no',
                $base_amount, $total_amount,
                $gst_amount, $cgst, $sgst, $igst, $gst_rate,
                '$payment_status', '$payment_mode', $paid_amount, $received_amount, " . ($payment_date ? "'$payment_date'" : "NULL") . ",
                $scrap_weight, $button_weight, $cornent_weight, $reminents_weight,
                '$narration', '$voucher_id', $is_jobs_wise, '$billing_type', '$excluded_job_ids',
                $round_off, '$bill_date', '$created_at', '$created_at', " . ($refer_party_id ? $refer_party_id : "NULL") . "
            )
        ";
        
        if (!$conn->query($insert_transactions)) {
            throw new Exception("Error saving transaction: " . $conn->error);
        }
        
        $transaction_id = $conn->insert_id;
        
        // 3. UPDATE job_cards table - mark as billed
        if ($job_id > 0) {
            $update_jobs = "
                UPDATE job_cards 
                SET is_billed = 1, 
                    bill_no = '$bill_number',
                    updated_at = '$created_at'
                WHERE id = $job_id AND firm_id = $firm_id
            ";
            
            if (!$conn->query($update_jobs)) {
                throw new Exception("Error updating job_cards: " . $conn->error);
            }
        }
        
        // 4. UPDATE jewellers table - credit balance
        if (!empty($licence_no)) {
            // Calculate remaining balance for credit
            $remaining_balance = $total_amount - $received_amount;
            
            if ($remaining_balance > 0) {
                $update_jewellers = "
                    UPDATE jewellers 
                    SET C_Bal = COALESCE(C_Bal, 0) + $remaining_balance,
                        updated_at = '$created_at'
                    WHERE licence_no = '$licence_no' AND firm_id = $firm_id
                ";
                
                if (!$conn->query($update_jewellers)) {
                    throw new Exception("Error updating jewellers: " . $conn->error);
                }
            }
        }
        
        // 5. INSERT into payment_receipts if payment received
        if ($received_amount > 0) {
            $receipt_no = "RCP/" . date('Y') . "/" . str_pad($firm_id, 3, '0', STR_PAD_LEFT) . "/" . str_pad($transaction_id, 4, '0', STR_PAD_LEFT);
            
            $insert_payment = "
                INSERT INTO payment_receipts (
                    bill_no, firm_id, receipt_no, payment_mode,
                    amount, payment_date, narration, created_at
                ) VALUES (
                    '$bill_number', $firm_id, '$receipt_no', '$payment_mode',
                    $received_amount, '$bill_date', 'Auto-payment from bill import', '$created_at'
                )
            ";
            
            if (!$conn->query($insert_payment)) {
                throw new Exception("Error creating payment receipt: " . $conn->error);
            }
        }
        
        // 6. Commit transaction
        $conn->commit();
        
        echo json_encode([
            "success" => true,
            "message" => "Bill imported and saved successfully",
            "saved" => true,
            "transaction_id" => $transaction_id,
            "bill_no" => $bill_number,
            "total_amount" => $total_amount,
            "payment_status" => $payment_status
        ]);
        
    } catch (Exception $e) {
        $conn->rollback();
        http_response_code(500);
        echo json_encode([
            "success" => false,
            "message" => "Error: " . $e->getMessage()
        ]);
    }

} else {
    echo json_encode(["success" => false, "message" => "Invalid action"]);
}

$conn->close();
?>
