from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
from bs4 import BeautifulSoup
from geocode import filter_by_radius, get_coordinates
from database import update_listing, get_db

def get_driver():
    """Initialize and return a Selenium WebDriver."""
    options = Options()
    options.add_argument("--headless")
    options.add_argument("user-agent=LocatorApp/1.0")
    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=options)

def scroll_and_get_source(driver, url, scrolls=3):
    """Scroll the page to load dynamic content and return the parsed HTML."""
    try:
        driver.get(url)
        time.sleep(5)  # Initial wait for page load
        for _ in range(scrolls):
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(3)  # Wait for content to load after each scroll
        return BeautifulSoup(driver.page_source, "html.parser")
    except Exception as e:
        print(f"Error accessing {url}: {e}")
        return BeautifulSoup("", "html.parser")

def scrape_seek(location, radius_km, keywords, category, lat, lon, city="", max_pages=20):
    """
    Scrape job listings from SEEK for a fixed number of pages (default 20).
    Saves jobs to the database as they are found to avoid losing progress.
    Avoids saving duplicate jobs by checking job links in the database.
    Uses 'N/A' for missing fields (except link) instead of skipping jobs.

    Args:
        location (str): Location for job search (e.g., "All Adelaide SA").
        radius_km (int): Radius for job search (not used in URL but can be for filtering).
        keywords (list or str): Main keywords for job search.
        category (str): Category like "part-time", "professional", or "aged-care".
        lat (float): Latitude for location (not used in this implementation).
        lon (float): Longitude for location (not used in this implementation).
        city (str): Optional city name (not used in this implementation).
        max_pages (int): Maximum number of pages to scrape (default 20).

    Returns:
        list: List of unique job dictionaries, including the keyword used for each job.
    """
    driver = get_driver()
    all_jobs = []
    seen_links = set()  # To track unique job links within this session
    db = get_db()
    collection = db["jobs"]

    # Define additional keywords for categories
    category_keywords = {
        "part-time": [
            "part time", "casual", "student", "urgent", "cash", "assistant", "helper", "temporary", "seasonal", "flexible hours", "evening shift", "weekend",
            "retail", "shop assistant", "sales assistant", "assistant", "store associate", "shop floor", "merchandise assistant", "supermarket", "cashier", "floor staff", "sales representative",
            "customer service", "front counter", "checkout", "store clerk", "retail support", "retail associate",
            "warehouse", "packer", "packaging", "labour", "loading", "unloading", "delivery driver", "courier", "driver", "van driver", "driver", "forklift",
            "logistics assistant", "warehouse operator", "material handler", "inventory", "receiving", "shipping", "stocking", "goods handling", "picker", "packer operator",
            "fulfillment", "warehouse packing", "warehouse staff", "distribution", "supply chain", "logistics",
            "cleaner", "cleaning", "housekeeping", "janitor", "groundskeeper", "maintenance assistant", "gardener", "maintenance", "facility support", "cleaning staff", "commercial cleaning",
            "office cleaning", "industrial cleaning", "floor cleaning", "sanitation",
            "office assistant", "admin assistant", "clerical", "office support", "data entry", "data processing", "customer support", "phone operator", "front desk", "document processing",
            "receptionist", "administration", "admin support", "call centre", "helpdesk", "office clerk", "virtual assistant", "remote work", "telemarketing", "back office",
            "event staff", "event assistant", "promoter", "brand ambassador", "usher", "ticketing", "casual staff", "temporary staff", "festival work", "promotional work", "roadshow",
            "exhibition", "conference staff", "hospitality casual", "staffing agency", "temp job", "marketing assistant",
            "childcare", "after school", "nanny", "babysitter", "au pair", "playgroup assistant", "daycare support", "preschool assistant",
            "labourer", "handyman", "delivery", "courier service", "pet care", "dog walker", "cleaning helper", "retail helper", "packing assistant", "stock assistant", "assistant worker",
            "general helper", "general labour", "warehouse helper", "store helper", "casual helper", "assistant packer"
        ],
        "professional": ["IT professional", "software engineer", "developer", "programmer"],
        "aged-care": ["aged care", "nursing", "care assistant"]
    }

    # Ensure keywords is a list
    if isinstance(keywords, str):
        keywords = [keywords]

    # Combine main keywords with category-specific keywords
    search_keywords = []
    for kw in keywords:
        if category in category_keywords:
            for cat_kw in category_keywords[category]:
                search_keywords.append(f"{kw} {cat_kw}".strip())
        else:
            search_keywords.append(kw)

    # Loop through all keywords to scrape
    for kw in search_keywords:
        for page in range(1, max_pages + 1):
            # Construct URL with page parameter
            url = f"https://www.seek.com.au/{kw.replace(' ', '-')}-jobs/in-{location.replace(' ', '-')}"
            if page > 1:
                url += f"?page={page}"
            
            print(f"Scraping page {page} for keyword: {kw}")
            soup = scroll_and_get_source(driver, url, scrolls=3)

            # Check if page has valid content
            if not soup:
                print(f"No content retrieved for page {page}, keyword: {kw}. Skipping.")
                break

            # Find job listings
            jobs_found = 0
            for job in soup.find_all("article", {"data-automation": "normalJob"}):
                try:
                    # Get job link
                    link_elem = job.find("a")
                    if not link_elem or "href" not in link_elem.attrs:
                        print(f"Skipping job with missing link on page {page}, keyword {kw}")
                        continue
                    link = "https://www.seek.com.au" + link_elem["href"]
                    
                    # Check for duplicate in database
                    if collection.find_one({"link": link}):
                        print(f"Duplicate job found in database (link: {link}). Skipping.")
                        continue
                    
                    # Check for duplicate in current session
                    if link in seen_links:
                        print(f"Duplicate job found in session (link: {link}). Skipping.")
                        continue

                    # Get job title
                    title_elem = job.find("a", {"data-automation": "jobTitle"})
                    title = title_elem.text.strip() if title_elem else "N/A"
                    
                    # Get company
                    company_elem = job.find("a", {"data-automation": "jobCompany"})
                    company = company_elem.text.strip() if company_elem else "N/A"
                    
                    # Get location
                    loc_elem = job.find("a", {"data-automation": "jobLocation"})
                    loc = loc_elem.text.strip() if loc_elem else "N/A"
                    
                    # Get posted date
                    posted_elem = job.find("span", {"data-automation": "jobListingDate"})
                    posted = posted_elem.text.strip() if posted_elem else None
                    deadline = None
                    
                    # Create job dictionary
                    job_data = {
                        "title": title,
                        "company": company,
                        "link": link,
                        "location": loc,
                        "source": "Seek",
                        "posted_date": posted,
                        "deadline_date": deadline,
                        "status": "new",
                        "keyword": kw,
                        "category": category
                    }
                    
                    # Save job to database immediately
                    try:
                        update_listing("jobs", link, job_data)
                        print(f"Saved job to database: {title} (link: {link})")
                    except Exception as e:
                        print(f"Error saving job to database (link: {link}): {e}")
                        continue
                    
                    all_jobs.append(job_data)
                    seen_links.add(link)
                    jobs_found += 1
                except Exception as e:
                    print(f"Error processing job on page {page}, keyword {kw}: {e}")
                    continue

            print(f"Found {jobs_found} jobs on page {page} for keyword: {kw}")
            
            # Stop early if no jobs found on this page
            if jobs_found == 0:
                print(f"No jobs found on page {page} for keyword: {kw}. Stopping.")
                break

            time.sleep(1)  # Small delay to avoid overwhelming the server

    driver.quit()
    return all_jobs

def scrape_custom(url, category, city=""):
    driver = get_driver()
    soup = scroll_and_get_source(driver, url, 2)
    jobs = []
    db = get_db()
    collection = db["jobs"]

    for job in soup.find_all("div", class_="post") or soup.find_all("li", class_="item"):
        try:
            # Get job link
            link_elem = job.find("a")
            link = link_elem["href"] if link_elem and "href" in link_elem.attrs else url
            
            # Check for duplicate in database
            if collection.find_one({"link": link}):
                print(f"Duplicate job found in database (link: {link}). Skipping.")
                continue
            
            # Get title
            title_elem = job.find("h2") or job.find("a")
            title = title_elem.text.strip() if title_elem else "N/A"
            
            # Get company
            company_elem = job.find("span", class_="company") or job.find("div", class_="employer")
            company = company_elem.text.strip() if company_elem else "N/A"
            
            # Get location
            loc_elem = job.find("span", class_="location") or job.find("div", class_="location")
            loc = loc_elem.text.strip() if loc_elem else "N/A"
            
            # Get posted date
            posted_elem = job.find("time") or job.find("span", class_="date")
            posted = posted_elem.get("datetime") or posted_elem.text.strip() if posted_elem else None
            
            # Get deadline
            deadline_elem = job.find("span", class_="deadline")
            deadline = deadline_elem.text.strip() if deadline_elem else None
            
            job_data = {
                "title": title,
                "company": company,
                "link": link,
                "location": loc,
                "source": "Custom",
                "posted_date": posted,
                "deadline_date": deadline,
                "status": "new",
                "category": category
            }
            
            # Save job to database immediately
            try:
                update_listing("jobs", link, job_data)
                print(f"Saved job to database: {title} (link: {link})")
            except Exception as e:
                print(f"Error saving job to database (link: {link}): {e}")
                continue
            
            jobs.append(job_data)
        except Exception:
            continue
    driver.quit()
    return jobs

def scrape_jobs(location, radius_km, keywords, category, lat, lon, city, custom_url=""):
    all_jobs = []
    site_functions = [
        (scrape_seek, "Seek"),
    ]
    total_sites = len(site_functions) + (1 if custom_url else 0)
    for idx, (func, site_name) in enumerate(site_functions):
        yield {"status": f"Scraping {site_name}...", "progress": (idx + 1) / total_sites}
        jobs = func(location, radius_km, keywords, category, lat, lon, city=city)
        all_jobs.extend(jobs)
    if custom_url:
        yield {"status": "Scraping custom URL...", "progress": 1.0}
        all_jobs.extend(scrape_custom(custom_url, category, city=city))
    seen = set()
    unique_jobs = []
    for job in all_jobs:
        if job["link"] not in seen:
            seen.add(job["link"])
            unique_jobs.append(job)
    yield {"status": "Completed", "progress": 1.0, "results": unique_jobs}