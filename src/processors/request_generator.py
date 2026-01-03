#!/usr/bin/env python3
"""
Request Generator Module
Extracted from manak_desktop_app.py to reduce file size
"""

import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


class RequestGenerator:
    """Handles request generation functionality"""
    
    def __init__(self, driver, log_callback, default_state_var, auto_fill_item_details_var):
        self.driver = driver
        self.log = log_callback
        self.default_state_var = default_state_var
        self.auto_fill_item_details_var = auto_fill_item_details_var
    
    def generate_single_request_internal(self, order):
        """Internal method to generate a single request"""
        try:
            # Step 1: Open generate request page
            self.log(f"🔗 Opening generate request page for order {order['order_no']}", 'generate')
            generate_url = "https://huid.manakonline.in/MANAK/AHC_RequestSubmission?cml_no=Q1JPL1JBSEMvUi0xMTAwNTg=&outletid=Mg==&EbranchId=OA==&requestno=&outletname=TUFIQUxBWE1JIEhBTExNQVJLIENFTlRSRQ=="
            self.driver.get(generate_url)
            time.sleep(1)
            
            # Step 2: Wait for page to load
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.TAG_NAME, "form"))
            )
            
            # Additional wait for Select2 elements to be ready
            try:
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".select2-container"))
                )
                self.log("✅ Select2 containers loaded", 'generate')
            except:
                self.log("⚠️ Select2 containers not found, proceeding anyway", 'generate')
            
            # Step 3: Select State using Select2
            self.log("🏛️ Selecting state...", 'generate')
            try:
                # Wait for page to fully load
                time.sleep(3)
                
                # Use state from order data if available, otherwise use default
                state_to_select = order.get('state', self.default_state_var.get())
                self.log(f"🎯 Attempting to select state: {state_to_select}", 'generate')
                
                # Use the helper method for Select2 selection
                state_selectors = [
                    "#s2id_state",
                    "[id*='state']",
                    ".select2-container[id*='state']",
                    ".select2-container:first-child"
                ]
                
                self._select_select2_option(state_selectors, state_to_select, "State")
                    
            except Exception as e:
                self.log(f"⚠️ Could not select state: {str(e)}", 'generate')
            
            # Step 4: Select Jeweller by License No using Select2
            self.log(f"👤 Selecting jeweller by license: {order['license_no']}", 'generate')
            try:
                # Wait for jeweller dropdown to be populated
                time.sleep(2)
                
                # Use the helper method for Select2 selection
                jeweller_selectors = [
                    "#s2id_jeweller",
                    "[id*='jeweller']",
                    ".select2-container[id*='jeweller']",
                    ".select2-container:nth-child(2)"  # Second select2 container
                ]
                
                self._select_select2_option(jeweller_selectors, order['license_no'], "Jeweller")
            except Exception as e:
                self.log(f"⚠️ Could not select jeweller: {str(e)}", 'generate')
            
            # Step 5: Click Add Items button
            self.log("➕ Clicking Add Items button...", 'generate')
            try:
                # First, try to close any open Select2 dropdowns that might be blocking
                try:
                    # Check if there's a select2-drop-mask overlay
                    mask = self.driver.find_element(By.CSS_SELECTOR, "#select2-drop-mask")
                    if mask.is_displayed():
                        # Click outside to close dropdown
                        self.driver.find_element(By.TAG_NAME, "body").click()
                        time.sleep(0.5)
                        self.log("✅ Closed Select2 dropdown overlay", 'generate')
                except:
                    pass
                
                # Wait a bit for any animations to complete
                time.sleep(1)
                
                # Try to find and click the Add Items button
                add_items_btn = self.driver.find_element(By.ID, "Adddata_btn")
                if add_items_btn.is_displayed() and add_items_btn.is_enabled():
                    # Try to scroll to the button first
                    self.driver.execute_script("arguments[0].scrollIntoView(true);", add_items_btn)
                    time.sleep(0.5)
                    
                    # Try clicking with JavaScript if regular click fails
                    try:
                        add_items_btn.click()
                    except:
                        self.driver.execute_script("arguments[0].click();", add_items_btn)
                    
                    time.sleep(1)
                    self.log("✅ Clicked Add Items button", 'generate')
                else:
                    raise Exception("Add Items button not interactable")
            except Exception as e:
                self.log(f"❌ Could not click Add Items button: {str(e)}", 'generate')
                return False
            
            # Step 6: Fill item details in dynamic form
            if self.auto_fill_item_details_var.get():
                self.log("📝 Filling item details...", 'generate')
                
                # Select Item Category using Select2
                try:
                    # Wait for the item category dropdown to be available
                    time.sleep(2)
                    
                    # Use the helper method for Select2 selection
                    category_selectors = [
                        "#s2id_itemCategory",
                        "[id*='itemCategory']",
                        "[id*='category']",
                        ".select2-container[id*='category']"
                    ]
                    
                    self._select_select2_option(category_selectors, "Ring", "Item Category")
                except Exception as e:
                    self.log(f"⚠️ Could not select item category: {str(e)}", 'generate')
                
                # Fill Item Weight
                try:
                    # Wait a bit for the form to load
                    time.sleep(1)
                    
                    # Try different possible selectors for weight field
                    weight_selectors = [
                        "input[name='itemWeight']",
                        "input[name='weight']", 
                        "input[id*='weight']",
                        "input[placeholder*='weight']",
                        "input[placeholder*='Weight']",
                        "input[type='text']",
                        "input[type='number']"
                    ]
                    
                    weight_field = None
                    for selector in weight_selectors:
                        try:
                            elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                            for element in elements:
                                if element.is_displayed() and element.is_enabled():
                                    # Check if this looks like a weight field
                                    placeholder = element.get_attribute('placeholder') or ''
                                    name = element.get_attribute('name') or ''
                                    if 'weight' in placeholder.lower() or 'weight' in name.lower() or not placeholder:
                                        weight_field = element
                                        self.log(f"✅ Found weight field with selector: {selector}", 'generate')
                                        break
                            if weight_field:
                                break
                        except:
                            continue
                    
                    if weight_field and weight_field.is_displayed():
                        # Scroll to the field
                        self.driver.execute_script("arguments[0].scrollIntoView(true);", weight_field)
                        time.sleep(0.5)
                        
                        weight_field.clear()
                        weight_field.send_keys(order['item_weight'])
                        self.log(f"✅ Filled item weight: {order['item_weight']}", 'generate')
                    else:
                        self.log("⚠️ Weight field not found", 'generate')
                except Exception as e:
                    self.log(f"⚠️ Could not fill item weight: {str(e)}", 'generate')
                
                # Select Purity using Select2
                try:
                    # Try to find purity dropdown
                    purity_selectors = [
                        "#s2id_purity",
                        "#s2id_purityType", 
                        "#s2id_karat"
                    ]
                    
                    purity_container = None
                    for selector in purity_selectors:
                        try:
                            purity_container = self.driver.find_element(By.CSS_SELECTOR, selector)
                            if purity_container.is_displayed():
                                break
                        except:
                            continue
                    
                    if purity_container:
                        purity_container.click()
                        time.sleep(0.5)
                        
                        # Extract purity value (e.g., "22K 916" -> "22K")
                        purity_value = order['purity'].split()[0] if ' ' in order['purity'] else order['purity']
                        
                        # Find the search input and type the purity
                        search_input = self.driver.find_element(By.CSS_SELECTOR, f"{purity_selectors[0]} .select2-input")
                        search_input.clear()
                        search_input.send_keys(purity_value)
                        time.sleep(1)
                        
                        # Select the first matching option
                        options = self.driver.find_elements(By.CSS_SELECTOR, f"{purity_selectors[0]} .select2-results li")
                        for option in options:
                            if purity_value in option.text:
                                option.click()
                                time.sleep(0.5)
                                self.log(f"✅ Selected purity: {order['purity']}", 'generate')
                                break
                    else:
                        self.log("⚠️ Purity dropdown not found", 'generate')
                except Exception as e:
                    self.log(f"⚠️ Could not select purity: {str(e)}", 'generate')
            
            # Step 7: Click Save button
            self.log("💾 Clicking Save button...", 'generate')
            try:
                # Wait a bit for any form processing
                time.sleep(2)
                
                # Try different possible selectors for Save button
                save_selectors = [
                    "//input[@type='button' and @value='Save']",
                    "//input[@type='submit' and @value='Save']",
                    "//button[contains(text(), 'Save')]",
                    "//input[@value='Save']",
                    "//button[@value='Save']",
                    "//input[contains(@class, 'save')]",
                    "//button[contains(@class, 'save')]",
                    "//input[@id='save_btn']",
                    "//button[@id='save_btn']",
                    "//input[contains(@onclick, 'save')]",
                    "//button[contains(@onclick, 'save')]"
                ]
                
                save_btn = None
                for selector in save_selectors:
                    try:
                        elements = self.driver.find_elements(By.XPATH, selector)
                        for element in elements:
                            if element.is_displayed() and element.is_enabled():
                                save_btn = element
                                self.log(f"✅ Found Save button with selector: {selector}", 'generate')
                                break
                        if save_btn:
                            break
                    except:
                        continue
                
                if save_btn and save_btn.is_displayed() and save_btn.is_enabled():
                    # Scroll to the button first
                    self.driver.execute_script("arguments[0].scrollIntoView(true);", save_btn)
                    time.sleep(0.5)
                    
                    # Try clicking with JavaScript if regular click fails
                    try:
                        save_btn.click()
                    except:
                        self.driver.execute_script("arguments[0].click();", save_btn)
                    
                    time.sleep(1)
                    self.log("✅ Clicked Save button", 'generate')
                else:
                    # If no Save button found, check if we need to submit the form differently
                    self.log("⚠️ Save button not found, checking for alternative submission methods", 'generate')
                    
                    # Try to find any submit button or form submission
                    submit_selectors = [
                        "//input[@type='submit']",
                        "//button[@type='submit']",
                        "//input[contains(@value, 'Submit')]",
                        "//button[contains(text(), 'Submit')]"
                    ]
                    
                    submit_btn = None
                    for selector in submit_selectors:
                        try:
                            elements = self.driver.find_elements(By.XPATH, selector)
                            for element in elements:
                                if element.is_displayed() and element.is_enabled():
                                    submit_btn = element
                                    self.log(f"✅ Found Submit button with selector: {selector}", 'generate')
                                    break
                            if submit_btn:
                                break
                        except:
                            continue
                    
                    if submit_btn:
                        self.driver.execute_script("arguments[0].scrollIntoView(true);", submit_btn)
                        time.sleep(0.5)
                        submit_btn.click()
                        time.sleep(1)
                        self.log("✅ Clicked Submit button instead of Save", 'generate')
                    else:
                        raise Exception("Save button not found or not interactable")
            except Exception as e:
                self.log(f"❌ Could not click Save button: {str(e)}", 'generate')
                return False
            
            # Step 8: Check if redirected to add more items page or if we need to wait for Save button
            current_url = self.driver.current_url
            self.log(f"📍 Current URL: {current_url}", 'generate')
            
            # Wait a bit more for any page transitions
            time.sleep(3)
            
            # Check if we're on a page with item details or if we need to look for different buttons
            if 'item_category=' in current_url or 'request' in current_url.lower():
                self.log("🔄 On request submission page", 'generate')
                
                # Step 9: Look for Submit to AHC or similar buttons
                try:
                    submit_selectors = [
                        "//input[@type='button' and contains(@value, 'Submit')]",
                        "//button[contains(text(), 'Submit')]",
                        "//input[contains(@value, 'Submit to AHC')]",
                        "//button[contains(text(), 'Submit to AHC')]",
                        "//input[@type='submit']",
                        "//button[@type='submit']"
                    ]
                    
                    submit_btn = None
                    for selector in submit_selectors:
                        try:
                            elements = self.driver.find_elements(By.XPATH, selector)
                            for element in elements:
                                if element.is_displayed() and element.is_enabled():
                                    submit_btn = element
                                    self.log(f"✅ Found Submit button with selector: {selector}", 'generate')
                                    break
                            if submit_btn:
                                break
                        except:
                            continue
                    
                    if submit_btn:
                        # Scroll to the button first
                        self.driver.execute_script("arguments[0].scrollIntoView(true);", submit_btn)
                        time.sleep(0.5)
                        
                        # Try clicking with JavaScript if regular click fails
                        try:
                            submit_btn.click()
                        except:
                            self.driver.execute_script("arguments[0].click();", submit_btn)
                        
                        time.sleep(1)
                        self.log("✅ Clicked Submit to AHC", 'generate')
                        
                        # Handle any confirmation dialogs
                        try:
                            alert = self.driver.switch_to.alert
                            alert_text = alert.text
                            self.log(f"🔔 Alert: {alert_text}", 'generate')
                            alert.accept()
                            time.sleep(0.5)
                        except:
                            pass
                            
                        return True
                    else:
                        self.log("⚠️ No Submit button found, checking if request was already submitted", 'generate')
                        # Check if there's any success message or if we're already on a success page
                        try:
                            success_indicators = [
                                "//*[contains(text(), 'success')]",
                                "//*[contains(text(), 'submitted')]",
                                "//*[contains(text(), 'request')]",
                                "//*[contains(@class, 'success')]"
                            ]
                            
                            for indicator in success_indicators:
                                try:
                                    element = self.driver.find_element(By.XPATH, indicator)
                                    if element.is_displayed():
                                        self.log(f"✅ Found success indicator: {element.text}", 'generate')
                                        return True
                                except:
                                    continue
                        except:
                            pass
                        
                        raise Exception("Submit button not found and no success indicators")
                except Exception as e:
                    self.log(f"❌ Could not click Submit to AHC: {str(e)}", 'generate')
                    return False
            else:
                self.log("⚠️ Not on expected request submission page", 'generate')
                # Try to find any other submission buttons
                try:
                    all_buttons = self.driver.find_elements(By.TAG_NAME, "button")
                    input_buttons = self.driver.find_elements(By.TAG_NAME, "input")
                    
                    for button in all_buttons + input_buttons:
                        if button.is_displayed() and button.is_enabled():
                            button_text = button.text or button.get_attribute('value') or ''
                            if any(keyword in button_text.lower() for keyword in ['submit', 'save', 'confirm', 'proceed']):
                                self.log(f"🔍 Found potential submission button: {button_text}", 'generate')
                                button.click()
                                time.sleep(1)
                                return True
                except:
                    pass
                
                return False
                
        except Exception as e:
            self.log(f"❌ Error in generate request workflow: {str(e)}", 'generate')
            return False

    def _select_select2_option(self, selectors, value, log_prefix):
        """Helper method to select Select2 options"""
        try:
            container = None
            for selector in selectors:
                try:
                    container = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if container.is_displayed():
                        break
                except:
                    continue
            
            if not container:
                raise Exception(f"No Select2 container found for {log_prefix}")
            
            container.click()
            time.sleep(0.5)
            
            # Find the search input and type the value
            search_input = self.driver.find_element(By.CSS_SELECTOR, f"{selectors[0]} .select2-input")
            search_input.clear()
            search_input.send_keys(value)
            time.sleep(1)
            
            # Select the first matching option
            options = self.driver.find_elements(By.CSS_SELECTOR, f"{selectors[0]} .select2-results li")
            for option in options:
                if value in option.text:
                    option.click()
                    time.sleep(0.5)
                    self.log(f"✅ Selected {log_prefix}: {value}", 'generate')
                    return True
            
            raise Exception(f"No matching option found for {log_prefix}: {value}")
            
        except Exception as e:
            self.log(f"⚠️ Could not select {log_prefix}: {str(e)}", 'generate')
            return False
