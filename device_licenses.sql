-- Device Licenses Table for MANAK Automation
-- Run this SQL script in your database to create the required table

CREATE TABLE IF NOT EXISTS `device_licenses` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `device_id` varchar(50) NOT NULL COMMENT 'MAC address or unique device identifier',
  `user_id` varchar(50) NOT NULL COMMENT 'User ID for the device',
  `status` enum('active','inactive','revoked','expired') NOT NULL DEFAULT 'active' COMMENT 'Device license status',
  `license_type` enum('standard','premium','trial') NOT NULL DEFAULT 'standard' COMMENT 'Type of license',
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'When device was registered',
  `expires_at` datetime NULL COMMENT 'License expiration date (NULL = never expires)',
  `last_verified` datetime NULL COMMENT 'Last time device was verified',
  `revoked_at` datetime NULL COMMENT 'When device was revoked (if applicable)',
  `notes` text NULL COMMENT 'Administrative notes',
  PRIMARY KEY (`id`),
  UNIQUE KEY `device_id` (`device_id`),
  KEY `user_id` (`user_id`),
  KEY `status` (`status`),
  KEY `expires_at` (`expires_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Device licenses for MANAK Automation application';

-- Insert sample data (optional)
-- INSERT INTO device_licenses (device_id, user_id, status, license_type, expires_at) VALUES
-- ('AA:BB:CC:DD:EE:FF', 'user001', 'active', 'standard', DATE_ADD(NOW(), INTERVAL 1 YEAR)),
-- ('11:22:33:44:55:66', 'user002', 'active', 'premium', DATE_ADD(NOW(), INTERVAL 2 YEAR));

-- Create index for better performance
CREATE INDEX idx_device_licenses_user_status ON device_licenses(user_id, status);
CREATE INDEX idx_device_licenses_expires ON device_licenses(expires_at); 