# 

import requests
from bs4 import BeautifulSoup
import json
import csv
import re
from urllib.parse import urljoin, urlparse
import time
from typing import List, Dict, Optional
import pandas as pd
import os

# Try to import Selenium for JavaScript-heavy pages
try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False
    print("Selenium not available. Install with: pip install selenium")
    print("Also download ChromeDriver from: https://chromedriver.chromium.org/")

class FacultyScraper:
    def __init__(self, use_selenium=False, deep_scrape=True, max_profile_visits=None):
        self.use_selenium = use_selenium and SELENIUM_AVAILABLE
        self.deep_scrape = deep_scrape
        self.max_profile_visits = max_profile_visits
        self.visited_urls = set()
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        
        if self.use_selenium:
            self.setup_selenium_driver()
    
    def setup_selenium_driver(self):
        """Setup Selenium WebDriver with appropriate options."""
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        
        try:
            self.driver = webdriver.Chrome(options=chrome_options)
        except Exception as e:
            print(f"Failed to setup Chrome driver: {e}")
            self.use_selenium = False
    
    def get_page_content(self, url: str) -> Optional[BeautifulSoup]:
        """Fetch and parse the webpage content."""
        if self.use_selenium:
            return self._get_content_selenium(url)
        else:
            return self._get_content_requests(url)
    
    def _get_content_requests(self, url: str) -> Optional[BeautifulSoup]:
        """Fetch content using requests."""
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            return BeautifulSoup(response.content, 'html.parser')
        except Exception as e:
            print(f"Error fetching {url} with requests: {e}")
            return None
    
    def _get_content_selenium(self, url: str) -> Optional[BeautifulSoup]:
        """Fetch content using Selenium (handles JavaScript)."""
        try:
            self.driver.get(url)
            time.sleep(3)  # Wait for content to load
            html = self.driver.page_source
            return BeautifulSoup(html, 'html.parser')
        except Exception as e:
            print(f"Error fetching {url} with Selenium: {e}")
            return None

    def scrape_faculty(self, url: str) -> List[Dict]:
        """Main method to scrape faculty from a URL."""
        print(f"Scraping faculty from: {url}")
        
        soup = self.get_page_content(url)
        if not soup:
            print("Failed to fetch page content")
            return []
        
        # Extract basic faculty info using profile containers
        faculty_list = self._extract_from_profiles(soup, url)
        
        print(f"Found {len(faculty_list)} faculty members")
        
        # Deep scrape individual profiles if enabled
        if self.deep_scrape and faculty_list:
            print(f"\nStarting deep scrape of individual faculty profiles...")
            faculty_list = self.deep_scrape_profiles(faculty_list)
        
        return faculty_list

    def _extract_from_profiles(self, soup: BeautifulSoup, base_url: str) -> List[Dict]:
        """Extract faculty from profile containers."""
        faculty_list = []
        
        # Find profile containers - adjust selector based on actual page structure
        profile_containers = soup.find_all('div', class_='profile')
        
        for container in profile_containers:
            faculty_info = {}
            
            # Extract name from h3
            name_elem = container.find('h3')
            if name_elem:
                faculty_info['name'] = name_elem.get_text(strip=True)
            
            # Extract title (usually after name)
            title_elem = container.find('p')
            if title_elem:
                title_text = title_elem.get_text(strip=True)
                if any(word in title_text.lower() for word in ['professor', 'lecturer', 'instructor']):
                    faculty_info['title'] = title_text
            
            # Extract email
            email_link = container.find('a', href=re.compile(r'^mailto:'))
            if email_link:
                email = email_link['href'].replace('mailto:', '')
                faculty_info['email'] = email
            
            # Extract phone
            phone_text = container.get_text()
            phone_match = re.search(r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}', phone_text)
            if phone_match:
                faculty_info['phone'] = phone_match.group(0)
            
            # Extract office
            office_match = re.search(r'Office:\s*([A-Z]{1,4}\s*\d+[A-Z]?)', container.get_text(), re.IGNORECASE)
            if office_match:
                faculty_info['office'] = office_match.group(1)
            
            # Extract profile URL
            profile_link = container.find('a', href=True)
            if profile_link and not profile_link['href'].startswith('mailto:'):
                faculty_info['profile_url'] = urljoin(base_url, profile_link['href'])
            
            # Extract image
            img = container.find('img')
            if img and img.get('src'):
                faculty_info['image_url'] = urljoin(base_url, img['src'])
            
            if faculty_info:  # Only add if we found some info
                faculty_list.append(faculty_info)
        
        return faculty_list

    def deep_scrape_profiles(self, faculty_list: List[Dict]) -> List[Dict]:
        """Visit individual faculty profile pages to extract detailed information."""
        enhanced_faculty = []
        max_visits = self.max_profile_visits or len(faculty_list)
        
        print(f"Will visit {min(max_visits, len(faculty_list))} profile pages")
        
        for i, faculty in enumerate(faculty_list):
            if i >= max_visits:
                # Add remaining faculty without deep scraping
                enhanced_faculty.extend(faculty_list[i:])
                break
                
            profile_url = faculty.get('profile_url')
            name = faculty.get('name', f'Faculty {i+1}')
            
            if profile_url:
                print(f"Scraping profile {i+1}/{min(max_visits, len(faculty_list))}: {name}")
                
                try:
                    detailed_info = self.scrape_individual_profile(profile_url)
                    # Merge detailed info with existing faculty info
                    enhanced_faculty_member = {**faculty, **detailed_info}
                    enhanced_faculty.append(enhanced_faculty_member)
                    
                    # Be respectful - delay between requests
                    time.sleep(2)
                    
                except Exception as e:
                    print(f"   Error scraping {name}'s profile: {e}")
                    enhanced_faculty.append(faculty)
            else:
                print(f"Skipping {name} - no profile URL")
                enhanced_faculty.append(faculty)
        
        return enhanced_faculty

    def scrape_individual_profile(self, profile_url: str) -> Dict:
        """Scrape detailed information from an individual faculty profile page."""
        soup = self.get_page_content(profile_url)
        if not soup:
            return {}
        
        detailed_info = {}
        
        # Extract research interests
        research_info = self._extract_detailed_research(soup)
        if research_info:
            detailed_info['research_interests'] = research_info
            print(f"   Found research interests: {research_info[:100]}...")
        
        # Extract education
        education = self._extract_education(soup)
        if education:
            detailed_info['education'] = education
            print(f"   Found education: {education[:50]}...")
        
        # Extract bio
        bio = self._extract_bio(soup)
        if bio:
            detailed_info['biography'] = bio[:500]  # Limit length
            print(f"   Found biography: {len(bio)} characters")
        
        return detailed_info

    def _extract_detailed_research(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract detailed research interests from profile page."""
        research_sections = []
        
        # Strategy 1: Look for headings with research-related keywords
        headings = soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
        research_keywords = ['research', 'interests', 'areas', 'focus']
        
        for heading in headings:
            heading_text = heading.get_text().lower()
            if any(keyword in heading_text for keyword in research_keywords):
                # Get content after this heading
                content = []
                current = heading.next_sibling
                
                while current:
                    if hasattr(current, 'name'):
                        if current.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                            break  # Stop at next heading
                        if current.name in ['p', 'div', 'ul', 'ol']:
                            text = current.get_text(strip=True)
                            if text and len(text) > 20:
                                content.append(text)
                    current = current.next_sibling
                
                if content:
                    research_sections.extend(content)
        
        # Strategy 2: Look for paragraphs with research keywords
        paragraphs = soup.find_all('p')
        research_keywords_extended = [
            'research', 'studying', 'investigating', 'focus', 'expertise',
            'specialization', 'interests include', 'work on', 'projects'
        ]
        
        for p in paragraphs:
            text = p.get_text()
            if any(keyword in text.lower() for keyword in research_keywords_extended):
                if len(text) > 50:  # Substantial content
                    research_sections.append(text.strip())
        
        # Strategy 3: Look for lists that might contain research topics
        lists = soup.find_all(['ul', 'ol'])
        for ul in lists:
            # Check if previous element suggests this is about research
            prev_sibling = ul.find_previous_sibling()
            if prev_sibling:
                prev_text = prev_sibling.get_text().lower()
                if any(keyword in prev_text for keyword in research_keywords):
                    items = [li.get_text(strip=True) for li in ul.find_all('li')]
                    if items:
                        research_sections.append('; '.join(items))
        
        if research_sections:
            # Remove duplicates and combine
            unique_sections = list(dict.fromkeys(research_sections))
            combined = ' | '.join(unique_sections)
            
            # Clean up text
            combined = re.sub(r'\s+', ' ', combined)
            return combined[:2000]  # Limit length
        
        return None

    def _extract_education(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract education information."""
        education_sections = []
        education_keywords = ['education', 'degrees', 'ph.d', 'phd', 'master', 'bachelor', 'university']
        
        # Look for headings with education keywords
        headings = soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
        for heading in headings:
            if any(keyword in heading.get_text().lower() for keyword in education_keywords):
                # Get content after heading
                current = heading.next_sibling
                while current:
                    if hasattr(current, 'name'):
                        if current.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                            break
                        if current.name in ['p', 'div', 'ul']:
                            text = current.get_text(strip=True)
                            if text and len(text) > 10:
                                education_sections.append(text)
                    current = current.next_sibling
        
        return ' | '.join(education_sections) if education_sections else None

    def _extract_bio(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract biography or about section."""
        bio_keywords = ['biography', 'about', 'bio', 'overview', 'background']
        
        # Look for headings with bio keywords
        headings = soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
        for heading in headings:
            if any(keyword in heading.get_text().lower() for keyword in bio_keywords):
                # Get content after heading
                bio_text = []
                current = heading.next_sibling
                while current:
                    if hasattr(current, 'name'):
                        if current.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                            break
                        if current.name == 'p':
                            text = current.get_text(strip=True)
                            if text and len(text) > 20:
                                bio_text.append(text)
                    current = current.next_sibling
                
                if bio_text:
                    return ' '.join(bio_text)
        
        return None

    def save_to_excel(self, faculty_list: List[Dict], filename: str = 'faculty.xlsx'):
        """Save faculty data to Excel file."""
        if not faculty_list:
            print("No faculty data to save")
            return
        
        df = pd.DataFrame(faculty_list)
        
        # Reorder columns for better readability
        preferred_columns = ['name', 'title', 'email', 'phone', 'office', 
                           'research_interests', 'education', 'biography', 
                           'profile_url', 'image_url']
        
        # Keep only columns that exist
        available_columns = [col for col in preferred_columns if col in df.columns]
        other_columns = [col for col in df.columns if col not in preferred_columns]
        
        if available_columns:
            df = df[available_columns + other_columns]
        
        # Save to Excel
        with pd.ExcelWriter(filename, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Faculty Directory', index=False)
            
            # Format the worksheet
            worksheet = writer.sheets['Faculty Directory']
            
            # Auto-adjust column widths
            for col_num, column in enumerate(df.columns, 1):
                column_letter = chr(64 + col_num)  # A, B, C, etc.
                if column == 'name':
                    worksheet.column_dimensions[column_letter].width = 25
                elif column == 'research_interests':
                    worksheet.column_dimensions[column_letter].width = 60
                elif column == 'education':
                    worksheet.column_dimensions[column_letter].width = 40
                elif column == 'biography':
                    worksheet.column_dimensions[column_letter].width = 50
                elif column in ['email', 'title']:
                    worksheet.column_dimensions[column_letter].width = 30
                else:
                    worksheet.column_dimensions[column_letter].width = 15
        
        print(f"Saved faculty data to {filename}")
        print(f"Total faculty members: {len(df)}")
        
        # Show statistics
        research_count = len([f for f in faculty_list if f.get('research_interests')])
        education_count = len([f for f in faculty_list if f.get('education')])
        bio_count = len([f for f in faculty_list if f.get('biography')])
        
        print(f"Faculty with research interests: {research_count}")
        print(f"Faculty with education info: {education_count}")
        print(f"Faculty with biography: {bio_count}")

    def __del__(self):
        """Clean up Selenium driver if it exists."""
        if hasattr(self, 'driver'):
            try:
                self.driver.quit()
            except:
                pass


# Simple script to run the scraper
if __name__ == "__main__":
    print(f"Files will be saved in: {os.getcwd()}")
    
    # Create scraper with deep scraping enabled
    scraper = FacultyScraper(
        use_selenium=True,
        deep_scrape=True,
        max_profile_visits=None # Start with 5 for testing
    )
    
    # Run the scraper
    faculty_data = scraper.scrape_faculty("https://sse.tulane.edu/cs/faculty")
    
    if faculty_data:
        # Save to Excel
        scraper.save_to_excel(faculty_data, 'tamu_faculty_detailed.xlsx')
        print(f"\nExcel file location: {os.path.join(os.getcwd(), 'tamu_faculty_detailed.xlsx')}")
    else:
        print("No faculty data found")