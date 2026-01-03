# Fire Assay Bulk Jobs - Lot Selection Fix

## Problem Description

When processing multiple jobs in the Fire Assay Bulk Jobs tab, the system was incorrectly selecting lots from different jobs. For example:

- When processing **Job 123682967**, the system would select **"Lot 1:123682008"** instead of the correct lot for Job 123682967
- This happened because the lot selection logic only matched based on lot number, ignoring which job the lot belonged to

## Root Cause

The `_select_lot_in_portal()` method in `multiple_jobs_processor.py` was matching lots based only on the lot number:

```python
# OLD LOGIC (INCORRECT)
if (option_text == f"Lot {lot_no}" or 
    option_text.endswith(f"Lot {lot_no}") or
    option_text.startswith(f"Lot {lot_no}:")):
```

This would match "Lot 1:123682008" when looking for "Lot 1", even if we were processing a different job.

## Solution

Modified the `_select_lot_in_portal()` method to:

1. **Accept a job_no parameter** to identify which job's lot we're looking for
2. **Prioritize exact matches** with the format "Lot X:JobNo"
3. **Fall back to plain "Lot X"** format if no job number is in the option text
4. **Log all available options** for better debugging

### New Logic

```python
# NEW LOGIC (CORRECT)
# Priority 1: Match "Lot X:JobNo" format when job_no is provided
if job_no and option_text == f"Lot {lot_no}:{job_no}":
    # Exact match with job number
    
# Priority 2: Match plain "Lot X" format (no job number suffix)
elif option_text == f"Lot {lot_no}" and ':' not in option_text:
    # Plain lot number without job suffix
```

## Changes Made

### 1. Updated `_select_lot_in_portal()` method (lines 1196-1255)
- Added `job_no` parameter
- Implemented priority-based matching logic
- Added debug logging to show all available lot options

### 2. Updated all method calls (3 locations)
- `_save_initial_weights_for_job()` - line 1421
- `_save_cornet_weights_for_job()` - line 1514  
- `_process_single_job_from_report()` - line 1173

All calls now pass the appropriate job number:
```python
self._select_lot_in_portal(str(lot_no), portal_job_no)
```

## Expected Behavior After Fix

When processing Job 123682967:
- ✅ Will correctly select "Lot 1:123682967" (if available)
- ✅ Will select "Lot 1" only if it has no job number suffix
- ❌ Will NOT select "Lot 1:123682008" (different job)

## Testing

To verify the fix:
1. Load a report with multiple jobs that have the same lot numbers
2. Select jobs to process in the Fire Assay Bulk Jobs tab
3. Click "Save Initial Weights" or "Save Cornet Weights"
4. Check the logs - you should see:
   - `🔍 DEBUG: Available lot options: [...]` - showing all available lots
   - `✅ Selected Lot X in portal (matched: 'Lot X:JobNo' with job JobNo)` - confirming correct selection

## Date
2025-12-14

## Files Modified
- `multiple_jobs_processor.py`

## Additional Fix: Missing Method

During testing, discovered that the `get_batch_job_statuses()` method was being called but didn't exist, causing:
```
❌ Database connection failed: Authentication plugin 'mysql_native_password' is not supported
❌ Error loading report data: 'NoneType' object has no attribute 'is_connected'
```

**Solution**: Added the missing `get_batch_job_statuses()` method (lines 2053-2106) that:
- Efficiently queries database status for multiple jobs in a single batch query
- Handles connection failures gracefully by returning default statuses
- Properly closes database connections after use
- Extracts original job numbers from lot-specific entries (e.g., "123684667 (Lot 1)" → "123684667")

