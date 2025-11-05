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

class AdaptiveFacultyScraper:
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
            time.sleep(3)
            html = self.driver.page_source
            return BeautifulSoup(html, 'html.parser')
        except Exception as e:
            print(f"Error fetching {url} with Selenium: {e}")
            return None

    def scrape_faculty(self, url: str) -> List[Dict]:
        """Main method to scrape faculty from any university URL."""
        print(f"Scraping faculty from: {url}")
        
        soup = self.get_page_content(url)
        if not soup:
            print("Failed to fetch page content")
            return []
        
        # Auto-detect the page structure and extract faculty
        faculty_list = self._auto_extract_faculty(soup, url)
        
        print(f"Found {len(faculty_list)} faculty members")
        
        # Deep scrape individual profiles if enabled
        if self.deep_scrape and faculty_list:
            print(f"Starting deep scrape of individual faculty profiles...")
            faculty_list = self.deep_scrape_profiles(faculty_list)
        
        return faculty_list

    def _auto_extract_faculty(self, soup: BeautifulSoup, base_url: str) -> List[Dict]:
        """Auto-detect faculty information using multiple adaptive strategies."""
        faculty_list = []
        
        print("Analyzing page structure...")
        
        # Strategy 1: Look for containers that likely contain faculty info
        potential_containers = self._find_faculty_containers(soup)
        print(f"Found {len(potential_containers)} potential faculty containers")
        
        for container in potential_containers:
            faculty_info = self._extract_faculty_from_container(container, base_url)
            if faculty_info and self._is_valid_faculty(faculty_info):
                faculty_list.append(faculty_info)
        
        # Strategy 2: Look for faculty in structured lists or tables
        list_faculty = self._extract_from_lists_and_tables(soup, base_url)
        for faculty in list_faculty:
            if faculty not in faculty_list and self._is_valid_faculty(faculty):
                faculty_list.append(faculty)
        
        # Remove duplicates
        faculty_list = self._remove_duplicates(faculty_list)
        
        return faculty_list

    def _find_faculty_containers(self, soup: BeautifulSoup) -> List:
        """Find containers that likely contain faculty information."""
        containers = []
        
        # Multiple selectors to catch different website structures
        selectors = [
            # Common patterns for faculty cards/profiles
            'div[class*="faculty"]',
            'div[class*="profile"]',
            'div[class*="person"]',
            'div[class*="member"]',
            'div[class*="staff"]',
            'article',
            'li[class*="faculty"]',
            'li[class*="profile"]',
            # Generic containers that might have faculty
            '.row > div',
            '.column > div',
            '.col > div',
            'div[class*="card"]',
            'div[class*="box"]',
        ]
        
        for selector in selectors:
            elements = soup.select(selector)
            for element in elements:
                if self._looks_like_faculty_container(element):
                    containers.append(element)
        
        # Also check direct children of common parent containers
        common_parents = soup.select('div[class*="faculty"], div[class*="directory"], div[class*="listing"], ul, ol')
        for parent in common_parents:
            for child in parent.find_all(['div', 'li'], recursive=False):
                if self._looks_like_faculty_container(child):
                    containers.append(child)
        
        return list(set(containers))  # Remove duplicates

    def _looks_like_faculty_container(self, element) -> bool:
        """Determine if an element likely contains faculty information."""
        text = element.get_text().strip().lower()
        
        # Must have some substantial content
        if len(text) < 20 or len(text) > 3000:
            return False
        
        # Look for faculty indicators
        faculty_indicators = [
            'professor', 'dr.', 'ph.d', 'phd', 'assistant', 'associate', 
            'chair', 'director', 'lecturer', 'instructor'
        ]
        has_title = any(indicator in text for indicator in faculty_indicators)
        
        # Look for email patterns
        has_email = bool(re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text))
        
        # Look for name patterns (First Last or Dr. First Last)
        has_name = bool(re.search(r'\b(?:dr\.?\s+)?[A-Z][a-z]+\s+[A-Z][a-z]+\b', element.get_text(), re.IGNORECASE))
        
        # Look for contact info
        has_phone = bool(re.search(r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}', text))
        
        # Look for office/room info
        has_office = bool(re.search(r'office|room|building', text))
        
        # Should have at least name + title OR name + email
        return (has_name and (has_title or has_email)) or (has_title and has_email)

    def _extract_faculty_from_container(self, container, base_url: str) -> Dict:
        """Extract faculty information from a container element."""
        faculty_info = {}
        text = container.get_text()
        
        # Extract name
        name = self._extract_name(container)
        if name:
            faculty_info['name'] = name
        
        # Extract title
        title = self._extract_title(text)
        if title:
            faculty_info['title'] = title
        
        # Extract email
        email = self._extract_email(container)
        if email:
            faculty_info['email'] = email
        
        # Extract phone
        phone = self._extract_phone(text)
        if phone:
            faculty_info['phone'] = phone
        
        # Extract office
        office = self._extract_office(text)
        if office:
            faculty_info['office'] = office
        
        # Extract profile URL
        profile_url = self._extract_profile_url(container, base_url)
        if profile_url:
            faculty_info['profile_url'] = profile_url
        
        # Extract image URL
        image_url = self._extract_image_url(container, base_url)
        if image_url:
            faculty_info['image_url'] = image_url
        
        return faculty_info

    def _extract_name(self, container) -> Optional[str]:
        """Extract faculty name from container using multiple strategies."""
        # Strategy 1: Look in headings
        for tag in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
            heading = container.find(tag)
            if heading:
                text = heading.get_text(strip=True)
                if self._looks_like_name(text):
                    return text
        
        # Strategy 2: Look in strong/bold text
        for strong in container.find_all(['strong', 'b']):
            text = strong.get_text(strip=True)
            if self._looks_like_name(text):
                return text
        
        # Strategy 3: Look in links
        for link in container.find_all('a'):
            text = link.get_text(strip=True)
            if self._looks_like_name(text) and not link.get('href', '').startswith('mailto:'):
                return text
        
        # Strategy 4: Use regex on the entire text
        text = container.get_text()
        # Look for patterns like "Dr. John Smith" or "John Smith, Ph.D."
        name_patterns = [
            r'\b(?:Dr\.?\s+)?([A-Z][a-z]+(?:\s+[A-Z][a-z]*\.?)?\s+[A-Z][a-z]+)\b',
            r'\b([A-Z][a-z]+\s+[A-Z][a-z]+)(?:\s*,\s*(?:Ph\.?D\.?|Professor))',
        ]
        
        for pattern in name_patterns:
            match = re.search(pattern, text)
            if match:
                name = match.group(1).strip()
                if self._looks_like_name(name):
                    return name
        
        return None

    def _looks_like_name(self, text: str) -> bool:
        """Check if text looks like a person's name."""
        if not text or len(text) > 50:
            return False
        
        words = text.split()
        if len(words) < 2 or len(words) > 4:
            return False
        
        # Should not contain numbers
        if any(char.isdigit() for char in text):
            return False
        
        # Should start with capital letters
        if not all(word[0].isupper() for word in words if word):
            return False
        
        # Exclude common non-names
        exclude_words = ['about', 'contact', 'research', 'education', 'department', 'university', 'college']
        if any(word.lower() in exclude_words for word in words):
            return False
        
        return True

    def _extract_title(self, text: str) -> Optional[str]:
        """Extract academic title."""
        title_patterns = [
            r'((?:Assistant|Associate|Full)?\s*Professor(?:\s+of\s+[A-Za-z\s]+)?)',
            r'(Chair(?:\s+of\s+[A-Za-z\s]+)?)',
            r'(Director(?:\s+of\s+[A-Za-z\s]+)?)',
            r'(Lecturer)',
            r'(Instructor)',
            r'(Research\s+(?:Professor|Scientist))',
        ]
        
        for pattern in title_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        return None

    def _extract_email(self, container) -> Optional[str]:
        """Extract email address."""
        # First try mailto links
        mailto_links = container.find_all('a', href=re.compile(r'^mailto:'))
        if mailto_links:
            return mailto_links[0]['href'].replace('mailto:', '').strip()
        
        # Then try text extraction
        text = container.get_text()
        email_match = re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text)
        return email_match.group(0) if email_match else None

    def _extract_phone(self, text: str) -> Optional[str]:
        """Extract phone number."""
        phone_patterns = [
            r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}',
            r'\+?1[-.\s]?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}'
        ]
        
        for pattern in phone_patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(0).strip()
        return None

    def _extract_office(self, text: str) -> Optional[str]:
        """Extract office location."""
        office_patterns = [
            r'(?:Office|Room|Building):?\s*([A-Z]{1,4}[-\s]*\d+[A-Z]?)',
            r'(?:Office|Room):?\s*(\d+[A-Z]?\s+[A-Z][a-z]+)',
        ]
        
        for pattern in office_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        return None

    def _extract_profile_url(self, container, base_url: str) -> Optional[str]:
        """Extract profile page URL."""
        links = container.find_all('a', href=True)
        
        # Look for explicit profile/bio links first
        for link in links:
            href = link['href']
            text = link.get_text().lower()
            if any(word in text for word in ['profile', 'bio', 'cv', 'more', 'details']):
                return urljoin(base_url, href)
        
        # Then look for name links (person's name as link text)
        name = self._extract_name(container)
        if name:
            for link in links:
                if name.lower() in link.get_text().lower():
                    href = link['href']
                    if not href.startswith('mailto:') and not href.startswith('#'):
                        return urljoin(base_url, href)
        
        # Finally, return first non-email link
        for link in links:
            href = link['href']
            if href and not href.startswith('mailto:') and not href.startswith('#'):
                return urljoin(base_url, href)
        
        return None

    def _extract_image_url(self, container, base_url: str) -> Optional[str]:
        """Extract faculty photo URL."""
        img = container.find('img')
        if img and img.get('src'):
            return urljoin(base_url, img['src'])
        return None

    def _extract_from_lists_and_tables(self, soup: BeautifulSoup, base_url: str) -> List[Dict]:
        """Extract faculty from structured lists or tables."""
        faculty_list = []
        
        # Look in tables
        tables = soup.find_all('table')
        for table in tables:
            rows = table.find_all('tr')
            for row in rows:
                cells = row.find_all(['td', 'th'])
                if len(cells) >= 2:  # At least name and something else
                    text = ' '.join(cell.get_text() for cell in cells)
                    if self._looks_like_faculty_container(BeautifulSoup(f'<div>{text}</div>', 'html.parser').div):
                        faculty_info = self._extract_faculty_from_container(row, base_url)
                        if faculty_info:
                            faculty_list.append(faculty_info)
        
        return faculty_list

    def _is_valid_faculty(self, faculty_info: Dict) -> bool:
        """Check if extracted faculty info is valid."""
        # Must have at least a name
        if not faculty_info.get('name'):
            return False
        
        # Should have at least one additional piece of info
        other_fields = ['title', 'email', 'phone', 'office', 'profile_url']
        return any(faculty_info.get(field) for field in other_fields)

    def _remove_duplicates(self, faculty_list: List[Dict]) -> List[Dict]:
        """Remove duplicate faculty entries."""
        seen = set()
        unique_faculty = []
        
        for faculty in faculty_list:
            # Use name and email as identifier
            name = faculty.get('name', '').lower().strip()
            email = faculty.get('email', '').lower().strip()
            
            identifier = (name, email)
            if identifier not in seen and name:
                seen.add(identifier)
                unique_faculty.append(faculty)
        
        return unique_faculty

    def deep_scrape_profiles(self, faculty_list: List[Dict]) -> List[Dict]:
        """Visit individual faculty profiles for detailed info."""
        enhanced_faculty = []
        max_visits = self.max_profile_visits or len(faculty_list)
        
        print(f"Will visit {min(max_visits, len(faculty_list))} profile pages")
        
        for i, faculty in enumerate(faculty_list):
            if i >= max_visits:
                enhanced_faculty.extend(faculty_list[i:])
                break
            
            profile_url = faculty.get('profile_url')
            name = faculty.get('name', f'Faculty {i+1}')
            
            if profile_url:
                print(f"Scraping profile {i+1}/{min(max_visits, len(faculty_list))}: {name}")
                
                try:
                    detailed_info = self.scrape_individual_profile(profile_url)
                    enhanced_faculty_member = {**faculty, **detailed_info}
                    enhanced_faculty.append(enhanced_faculty_member)
                    time.sleep(1)  # Be respectful
                except Exception as e:
                    print(f"   Error: {e}")
                    enhanced_faculty.append(faculty)
            else:
                enhanced_faculty.append(faculty)
        
        return enhanced_faculty

    def scrape_individual_profile(self, profile_url: str) -> Dict:
        """Scrape detailed info from individual profile."""
        soup = self.get_page_content(profile_url)
        if not soup:
            return {}
        
        detailed_info = {}
        
        # Extract research interests
        research = self._extract_research_interests(soup)
        if research:
            detailed_info['research_interests'] = research
            print(f"   Found research: {research[:50]}...")
        
        # Extract education
        education = self._extract_education(soup)
        if education:
            detailed_info['education'] = education
        
        # Extract bio
        bio = self._extract_biography(soup)
        if bio:
            detailed_info['biography'] = bio[:500]
        
        return detailed_info

    def _extract_research_interests(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract research interests from profile page."""
        research_sections = []
        research_keywords = ['research', 'interests', 'areas', 'focus', 'specialization']
        
        # Look for headings with research keywords
        headings = soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
        for heading in headings:
            heading_text = heading.get_text().lower()
            if any(keyword in heading_text for keyword in research_keywords):
                # Get content after heading
                current = heading.next_sibling
                content_parts = []
                
                while current and len(content_parts) < 5:  # Limit to avoid too much
                    if hasattr(current, 'name'):
                        if current.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                            break
                        if current.name in ['p', 'div', 'ul', 'li']:
                            text = current.get_text(strip=True)
                            if text and len(text) > 20:
                                content_parts.append(text)
                    current = current.next_sibling
                
                if content_parts:
                    research_sections.extend(content_parts)
        
        # Also look for paragraphs with research keywords
        paragraphs = soup.find_all('p')
        for p in paragraphs:
            text = p.get_text()
            if any(keyword in text.lower() for keyword in research_keywords) and len(text) > 50:
                research_sections.append(text.strip())
        
        if research_sections:
            combined = ' | '.join(research_sections[:3])  # Limit to first 3 sections
            return re.sub(r'\s+', ' ', combined)[:1500]  # Clean and limit length
        
        return None

    def _extract_education(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract education information."""
        education_keywords = ['education', 'degrees', 'phd', 'ph.d', 'master', 'bachelor', 'university']
        
        # Look for education sections
        headings = soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
        for heading in headings:
            if any(keyword in heading.get_text().lower() for keyword in education_keywords):
                current = heading.next_sibling
                education_parts = []
                
                while current and len(education_parts) < 3:
                    if hasattr(current, 'name'):
                        if current.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                            break
                        if current.name in ['p', 'div', 'ul']:
                            text = current.get_text(strip=True)
                            if text and len(text) > 10:
                                education_parts.append(text)
                    current = current.next_sibling
                
                if education_parts:
                    return ' | '.join(education_parts)
        
        return None

    def _extract_biography(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract biography."""
        bio_keywords = ['biography', 'about', 'bio', 'overview', 'background']
        
        headings = soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
        for heading in headings:
            if any(keyword in heading.get_text().lower() for keyword in bio_keywords):
                current = heading.next_sibling
                bio_parts = []
                
                while current and len(' '.join(bio_parts)) < 1000:  # Limit bio length
                    if hasattr(current, 'name'):
                        if current.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                            break
                        if current.name == 'p':
                            text = current.get_text(strip=True)
                            if text and len(text) > 20:
                                bio_parts.append(text)
                    current = current.next_sibling
                
                if bio_parts:
                    return ' '.join(bio_parts)
        
        return None

    # def save_to_excel(self, faculty_list: List[Dict], filename: str = 'faculty.xlsx'):
    #     """Save faculty data to Excel."""
    #     if not faculty_list:
    #         print("No faculty data to save")
    #         return
        
    #     df = pd.DataFrame(faculty_list)
        
    #     # Reorder columns
    #     preferred_order = ['name', 'title', 'email', 'phone', 'office', 
    #                       'research_interests', 'education', 'biography', 
    #                       'profile_url', 'image_url']
        
    #     available_cols = [col for col in preferred_order if col in df.columns]
    #     other_cols = [col for col in df.columns if col not in preferred_order]
        
    #     if available_cols:
    #         df = df[available_cols + other_cols]
        
    #     # Save with formatting
    #     with pd.ExcelWriter(filename, engine='openpyxl') as writer:
    #         df.to_excel(writer, sheet_name='Faculty Directory', index=False)
            
    #         worksheet = writer.sheets['Faculty Directory']
            
    #         # Set column widths
    #         column_widths = {
    #             'name': 25, 'title': 30, 'email': 30, 'phone': 15, 'office': 15,
    #             'research_interests': 60, 'education': 40, 'biography': 50,
    #             'profile_url': 40, 'image_url': 40
    #         }
            
    #         for i, column in enumerate(df.columns, 1):
    #             col_letter = chr(64 + i)
    #             width = column_widths.get(column, 20)
    #             worksheet.column_dimensions[col_letter].width = width
        
    #     print(f"Saved to {filename}")
    #     print(f"Total faculty: {len(df)}")
        
    #     # Show stats
    #     stats = {
    #         'research_interests': len([f for f in faculty_list if f.get('research_interests')]),
    #         'education': len([f for f in faculty_list if f.get('education')]),
    #         'biography': len([f for f in faculty_list if f.get('biography')])
    #     }
        
    #     for field, count in stats.items():
    #         if count > 0:
    #             print(f"Faculty with {field}: {count}")


    def save_to_excel(self, faculty_list: List[Dict], filename: str = 'faculty.xlsx'):
        """Save faculty data to Excel into faculty_scraping_quick folder."""
        if not faculty_list:
            print("No faculty data to save")
            return

        # Ensure the output directory exists
        output_dir = os.path.join(os.getcwd(), "faculty_scraping_quick")
        os.makedirs(output_dir, exist_ok=True)

        # Build full path
        file_path = os.path.join(output_dir, filename)

        df = pd.DataFrame(faculty_list)

        # Reorder columns
        preferred_order = ['name', 'title', 'email', 'phone', 'office',
                          'research_interests', 'education', 'biography',
                          'profile_url', 'image_url']

        available_cols = [col for col in preferred_order if col in df.columns]
        other_cols = [col for col in df.columns if col not in preferred_order]

        if available_cols:
            df = df[available_cols + other_cols]

        # Save with formatting
        with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Faculty Directory', index=False)

            worksheet = writer.sheets['Faculty Directory']

            # Set column widths
            column_widths = {
                'name': 25, 'title': 30, 'email': 30, 'phone': 15, 'office': 15,
                'research_interests': 60, 'education': 40, 'biography': 50,
                'profile_url': 40, 'image_url': 40
            }

            for i, column in enumerate(df.columns, 1):
                col_letter = chr(64 + i)
                width = column_widths.get(column, 20)
                worksheet.column_dimensions[col_letter].width = width

        print(f"Saved to {file_path}")
        print(f"Total faculty: {len(df)}")

        # Show stats
        stats = {
            'research_interests': len([f for f in faculty_list if f.get('research_interests')]),
            'education': len([f for f in faculty_list if f.get('education')]),
            'biography': len([f for f in faculty_list if f.get('biography')])
        }

        for field, count in stats.items():
            if count > 0:
                print(f"Faculty with {field}: {count}")

    def __del__(self):
        if hasattr(self, 'driver'):
            try:
                self.driver.quit()
            except:
                pass


# Simple usage
if __name__ == "__main__":
    print(f"Files will be saved in: {os.getcwd()}")
    
    # Test with Texas Tech
    scraper = AdaptiveFacultyScraper(
        use_selenium=True,
        deep_scrape=True,
        max_profile_visits=None
    )
    
    faculty_data = scraper.scrape_faculty("https://sse.tulane.edu/cs/faculty")
    
    if faculty_data:
        scraper.save_to_excel(faculty_data, 'ttu_faculty_detailed.xlsx')
        print(f"Excel file saved in: {os.path.join(os.getcwd(), 'faculty_scraping_quick', 'ttu_faculty_detailed.xlsx')}")

    else:
        print("No faculty data found")