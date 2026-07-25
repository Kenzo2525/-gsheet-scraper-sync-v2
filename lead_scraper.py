import gspread
import requests
from bs4 import BeautifulSoup
import time
import re
from datetime import date

# 1. Authenticate with Google Sheets
gc = gspread.service_account(filename='credentials.json')
SPREADSHEET_KEY = "1_efCeFKjb_b31CG7MnQ15PXNi3doQxsUGxj03zDR1DM"

try:
    sh = gc.open_by_key(SPREADSHEET_KEY)
    worksheet = sh.sheet1
    print("[*] Successfully connected to your Google Sheet!")
except Exception as e:
    print(f"[-] Connection Error: {e}")
    exit(1)

# Ensure Header Row includes Email column
headers = ["Business Name", "Website/Source", "Email Address", "Niche Target", "Location", "Date Added", "Outreach Status"]
if len(worksheet.get_all_values()) == 0:
    worksheet.append_row(headers)

REQUEST_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36"
}

# Regex pattern for matching standard email addresses
EMAIL_REGEX = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'

def extract_email_from_website(website_url):
    """
    Visits the target website and extracts public contact emails.
    """
    if not website_url.startswith('http'):
        website_url = f"https://{website_url}"
        
    try:
        res = requests.get(website_url, headers=REQUEST_HEADERS, timeout=6)
        if res.status_code == 200:
            found_emails = re.findall(EMAIL_REGEX, res.text)
            
            # Filter out common false positives and image files
            valid_emails = [
                e for e in found_emails 
                if not any(junk in e.lower() for junk in ['.png', '.jpg', '.jpeg', '.svg', 'wixpress', 'sentry', 'domain.com', 'example.com', 'schema.org'])
            ]
            
            if valid_emails:
                # Return the first clean email found
                return list(set(valid_emails))[0]
    except Exception:
        pass # Silently skip if site blocks scraping or times out
        
    return "Not Found"

def extract_live_b2b_leads(niche_keyword, target_location, max_results=25):
    print(f"\n[🚀] Extracting Premium Leads: '{niche_keyword}' in '{target_location}'")
    
    search_query = f"{niche_keyword} in {target_location} contact website"
    search_url = f"https://html.duckduckgo.com/html/?q={requests.utils.quote(search_query)}"
    
    try:
        response = requests.get(search_url, headers=REQUEST_HEADERS, timeout=10)
        if response.status_code != 200:
            print("[-] Rate limited or temporary connection error. Waiting 30s...")
            return

        soup = BeautifulSoup(response.text, 'html.parser')
        results = soup.find_all('div', class_='result')
        
        saved_count = 0
        for result in results:
            if saved_count >= max_results:
                break
                
            title_tag = result.find('a', class_='result__a')
            
            if title_tag:
                company_name = title_tag.get_text(strip=True)
                website_link = title_tag.get('href', '')
                
                # Filter out generic platforms/directories
                if any(ignored in website_link for ignored in ['wikipedia', 'youtube', 'facebook', 'instagram', 'twitter']):
                    continue

                # Scan website for direct contact email
                print(f"  [🔍] Scanning {company_name} for contact email...")
                contact_email = extract_email_from_website(website_link)

                lead_data = [
                    company_name,
                    website_link,
                    contact_email,
                    niche_keyword,
                    target_location,
                    str(date.today()),
                    "Not Contacted"
                ]
                
                worksheet.append_row(lead_data)
                saved_count += 1
                print(f"  [+] Saved ({saved_count}/{max_results}): {company_name} | Email: {contact_email}")
                time.sleep(2) # Friendly request throttle
                
        print(f"[✓] Complete! Added {saved_count} enriched leads to Google Sheets.")

    except Exception as e:
        print(f"[-] Error during scraping: {e}")

if __name__ == "__main__":
    # Test Run with Email Extraction: 10 E-Commerce Agencies in New York
    extract_live_b2b_leads(niche_keyword="Shopify Development Agency", target_location="New York US", max_results=25)