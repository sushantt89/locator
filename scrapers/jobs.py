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

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
import time

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
        list: List of job dictionaries, including the keyword used for each job.
    """
    driver = get_driver()
    all_jobs = []

    # Define additional keywords for categories
    category_keywords = {
        "part-time": ["warehouse"],
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
                    title = job.find("a", {"data-automation": "jobTitle"}).text.strip()
                    link = "https://www.seek.com.au" + job.find("a")["href"]
                    company = job.find("a", {"data-automation": "jobCompany"}).text.strip()
                    loc = job.find("a", {"data-automation": "jobLocation"}).text.strip()
                    posted = job.find("span", {"data-automation": "jobListingDate"}).text.strip() if job.find("span", {"data-automation": "jobListingDate"}) else None
                    deadline = None
                    all_jobs.append({
                        "title": title,
                        "company": company,
                        "link": link,
                        "location": loc,
                        "source": "Seek",
                        "posted_date": posted,
                        "deadline_date": deadline,
                        "status": "new",
                        "keyword": kw  # Add keyword to track which search term found this job
                    })
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

def scrape_indeed(location, radius_km, keywords, category, lat, lon, city=""):
    driver = get_driver()
    base_keywords = keywords
    if category == "part-time":
        base_keywords += " part time casual student"
    elif category == "professional":
        base_keywords += " IT professional"
    elif category == "aged-care":
        base_keywords = "aged care " + base_keywords
    url = f"https://au.indeed.com/jobs?q={base_keywords.replace(' ', '+')}&l={location.replace(' ', '+')}&radius={radius_km}"
    soup = scroll_and_get_source(driver, url, 2)
    jobs = []
    for job in soup.find_all("div", class_="jobsearch-SerpJobCard"):
        try:
            title = job.find("h2", class_="title").text.strip()
            link = "https://au.indeed.com" + job.find("a", class_="jobtitle")["href"]
            company = job.find("span", class_="company").text.strip()
            loc = job.find("span", class_="location").text.strip()
            posted = job.find("span", class_="date").text.strip() if job.find("span", class_="date") else None
            deadline = None
            jobs.append({"title": title, "company": company, "link": link, "location": loc, "source": "Indeed", "posted_date": posted, "deadline_date": deadline, "status": "new"})
        except Exception:
            continue
    driver.quit()
    return filter_by_radius(jobs, lat, lon, radius_km)

def scrape_jora(location, radius_km, keywords, category, lat, lon, city=""):
    driver = get_driver()
    base_keywords = keywords
    if category == "part-time":
        base_keywords += " part time casual student"
    elif category == "professional":
        base_keywords += " IT professional"
    elif category == "aged-care":
        base_keywords = "aged care " + base_keywords
    url = f"https://au.jora.com/{base_keywords.replace(' ', '-')}-jobs-in-{location.replace(' ', '-')}"
    soup = scroll_and_get_source(driver, url, 2)
    jobs = []
    for job in soup.find_all("div", class_="job-card"):
        try:
            title = job.find("h2", class_="job-title").text.strip()
            link = "https://au.jora.com" + job.find("a")["href"]
            company = job.find("span", class_="company").text.strip()
            loc = job.find("span", class_="location").text.strip()
            posted = job.find("span", class_="date").text.strip() if job.find("span", class_="date") else None
            deadline = None
            jobs.append({"title": title, "company": company, "link": link, "location": loc, "source": "Jora", "posted_date": posted, "deadline_date": deadline, "status": "new"})
        except Exception:
            continue
    driver.quit()
    return filter_by_radius(jobs, lat, lon, radius_km)

def scrape_linkedin(location, radius_km, keywords, category, lat, lon, city=""):
    driver = get_driver()
    base_keywords = keywords
    if category == "part-time":
        base_keywords += " part time casual student"
    elif category == "professional":
        base_keywords += " IT professional"
    elif category == "aged-care":
        base_keywords = "aged care " + base_keywords
    url = f"https://www.linkedin.com/jobs/search/?keywords={base_keywords.replace(' ', '%20')}&location={location.replace(' ', '%20')}&distance={radius_km}"
    soup = scroll_and_get_source(driver, url, 2)
    jobs = []
    for job in soup.find_all("li", class_="job-result-card"):
        try:
            title = job.find("h3", class_="job-result-card__title").text.strip()
            link = job.find("a", class_="result-card__full-card-link")["href"]
            company = job.find("h4", class_="job-result-card__subtitle").text.strip()
            loc = job.find("span", class_="job-result-card__location").text.strip()
            posted = job.find("time", class_="job-result-card__posted-date").text.strip() if job.find("time", class_="job-result-card__posted-date") else None
            deadline = None
            jobs.append({"title": title, "company": company, "link": link, "location": loc, "source": "LinkedIn", "posted_date": posted, "deadline_date": deadline, "status": "new"})
        except Exception:
            continue
    driver.quit()
    return filter_by_radius(jobs, lat, lon, radius_km)

def scrape_glassdoor(location, radius_km, keywords, category, lat, lon, city=""):
    driver = get_driver()
    base_keywords = keywords
    if category == "part-time":
        base_keywords += " part time casual student"
    elif category == "professional":
        base_keywords += " IT professional"
    elif category == "aged-care":
        base_keywords = "aged care " + base_keywords
    url = f"https://www.glassdoor.com.au/Job/{base_keywords.replace(' ', '-')}-jobs-SRCH_KO0,{len(base_keywords.replace(' ', '-'))}_IL.0,{len(location.replace(' ', '-'))}_IP{location.replace(' ', '-')}.htm?radius={radius_km}"
    soup = scroll_and_get_source(driver, url, 2)
    jobs = []
    for job in soup.find_all("li", class_="jobListing"):
        try:
            title = job.find("a", class_="jobLink").text.strip()
            link = job.find("a", class_="jobLink")["href"]
            company = job.find("div", class_="jobEmp").text.strip()
            loc = job.find("span", class_="jobLoc").text.strip()
            posted = job.find("span", class_="jobDate").text.strip() if job.find("span", class_="jobDate") else None
            deadline = None
            jobs.append({"title": title, "company": company, "link": link, "location": loc, "source": "Glassdoor", "posted_date": posted, "deadline_date": deadline, "status": "new"})
        except Exception:
            continue
    driver.quit()
    return filter_by_radius(jobs, lat, lon, radius_km)

def scrape_careerone(location, radius_km, keywords, category, lat, lon, city=""):
    driver = get_driver()
    base_keywords = keywords
    if category == "part-time":
        base_keywords += " part time casual student"
    elif category == "professional":
        base_keywords += " IT professional"
    elif category == "aged-care":
        base_keywords = "aged care " + base_keywords
    url = f"https://www.careerone.com.au/{base_keywords.replace(' ', '-')}-jobs/in-{location.replace(' ', '-')}"
    soup = scroll_and_get_source(driver, url, 2)
    jobs = []
    for job in soup.find_all("div", class_="job"):
        try:
            title = job.find("h2").text.strip()
            link = job.find("a")["href"]
            company = job.find("span", class_="company").text.strip()
            loc = job.find("span", class_="location").text.strip()
            posted = job.find("span", class_="date").text.strip() if job.find("span", class_="date") else None
            deadline = None
            jobs.append({"title": title, "company": company, "link": link, "location": loc, "source": "CareerOne", "posted_date": posted, "deadline_date": deadline, "status": "new"})
        except Exception:
            continue
    driver.quit()
    return filter_by_radius(jobs, lat, lon, radius_km)

def scrape_adzuna(location, radius_km, keywords, category, lat, lon, city=""):
    driver = get_driver()
    base_keywords = keywords
    if category == "part-time":
        base_keywords += " part time casual student"
    elif category == "professional":
        base_keywords += " IT professional"
    elif category == "aged-care":
        base_keywords = "aged care " + base_keywords
    url = f"https://www.adzuna.com.au/search?loc={location.replace(' ', '+')}&q={base_keywords.replace(' ', '+')}"
    soup = scroll_and_get_source(driver, url, 2)
    jobs = []
    for job in soup.find_all("div", class_="job-card"):
        try:
            title = job.find("h2").text.strip()
            link = job.find("a")["href"]
            company = job.find("span", class_="company").text.strip()
            loc = job.find("span", class_="location").text.strip()
            posted = job.find("span", class_="date").text.strip() if job.find("span", class_="date") else None
            deadline = None
            jobs.append({"title": title, "company": company, "link": link, "location": loc, "source": "Adzuna", "posted_date": posted, "deadline_date": deadline, "status": "new"})
        except Exception:
            continue
    driver.quit()
    return filter_by_radius(jobs, lat, lon, radius_km)

def scrape_apsjobs(location, radius_km, keywords, category, lat, lon, city=""):
    driver = get_driver()
    base_keywords = keywords
    if category == "part-time":
        base_keywords += " part time casual student"
    elif category == "professional":
        base_keywords += " IT professional"
    elif category == "aged-care":
        base_keywords = "aged care " + base_keywords
    url = f"https://www.apsjobs.gov.au/s/search-jobs?query={base_keywords.replace(' ', '+')}&location={location.replace(' ', '+')}"
    soup = scroll_and_get_source(driver, url, 2)
    jobs = []
    for job in soup.find_all("div", class_="job"):
        try:
            title = job.find("h3").text.strip()
            link = job.find("a")["href"]
            company = job.find("span", class_="agency").text.strip()
            loc = job.find("span", class_="location").text.strip()
            posted = job.find("span", class_="date").text.strip() if job.find("span", class_="date") else None
            deadline = None
            jobs.append({"title": title, "company": company, "link": link, "location": loc, "source": "APSJobs", "posted_date": posted, "deadline_date": deadline, "status": "new"})
        except Exception:
            continue
    driver.quit()
    return filter_by_radius(jobs, lat, lon, radius_km)

def scrape_jobsvic(location, radius_km, keywords, category, lat, lon, city=""):
    driver = get_driver()
    base_keywords = keywords
    if category == "part-time":
        base_keywords += " part time casual student"
    elif category == "professional":
        base_keywords += " IT professional"
    elif category == "aged-care":
        base_keywords = "aged care " + base_keywords
    url = f"https://jobs.vic.gov.au/jobs?query={base_keywords.replace(' ', '+')}&location={location.replace(' ', '+')}"
    soup = scroll_and_get_source(driver, url, 2)
    jobs = []
    for job in soup.find_all("div", class_="job"):
        try:
            title = job.find("h3").text.strip()
            link = job.find("a")["href"]
            company = job.find("span", class_="department").text.strip()
            loc = job.find("span", class_="location").text.strip()
            posted = job.find("span", class_="date").text.strip() if job.find("span", class_="date") else None
            deadline = None
            jobs.append({"title": title, "company": company, "link": link, "location": loc, "source": "JobsVIC", "posted_date": posted, "deadline_date": deadline, "status": "new"})
        except Exception:
            continue
    driver.quit()
    return filter_by_radius(jobs, lat, lon, radius_km)

def scrape_smartjobs(location, radius_km, keywords, category, lat, lon, city=""):
    driver = get_driver()
    base_keywords = keywords
    if category == "part-time":
        base_keywords += " part time casual student"
    elif category == "professional":
        base_keywords += " IT professional"
    elif category == "aged-care":
        base_keywords = "aged care " + base_keywords
    url = f"https://smartjobs.qld.gov.au/jobs?query={base_keywords.replace(' ', '+')}&location={location.replace(' ', '+')}"
    soup = scroll_and_get_source(driver, url, 2)
    jobs = []
    for job in soup.find_all("div", class_="job"):
        try:
            title = job.find("h3").text.strip()
            link = job.find("a")["href"]
            company = job.find("span", class_="department").text.strip()
            loc = job.find("span", class_="location").text.strip()
            posted = job.find("span", class_="date").text.strip() if job.find("span", class_="date") else None
            deadline = None
            jobs.append({"title": title, "company": company, "link": link, "location": loc, "source": "SmartJobs", "posted_date": posted, "deadline_date": deadline, "status": "new"})
        except Exception:
            continue
    driver.quit()
    return filter_by_radius(jobs, lat, lon, radius_km)

def scrape_jobswa(location, radius_km, keywords, category, lat, lon, city=""):
    driver = get_driver()
    base_keywords = keywords
    if category == "part-time":
        base_keywords += " part time casual student"
    elif category == "professional":
        base_keywords += " IT professional"
    elif category == "aged-care":
        base_keywords = "aged care " + base_keywords
    url = f"https://jobs.wa.gov.au/jobs?query={base_keywords.replace(' ', '+')}&location={location.replace(' ', '+')}"
    soup = scroll_and_get_source(driver, url, 2)
    jobs = []
    for job in soup.find_all("div", class_="job"):
        try:
            title = job.find("h3").text.strip()
            link = job.find("a")["href"]
            company = job.find("span", class_="department").text.strip()
            loc = job.find("span", class_="location").text.strip()
            posted = job.find("span", class_="date").text.strip() if job.find("span", class_="date") else None
            deadline = None
            jobs.append({"title": title, "company": company, "link": link, "location": loc, "source": "JobsWA", "posted_date": posted, "deadline_date": deadline, "status": "new"})
        except Exception:
            continue
    driver.quit()
    return filter_by_radius(jobs, lat, lon, radius_km)

def scrape_ethicaljobs(location, radius_km, keywords, category, lat, lon, city=""):
    driver = get_driver()
    base_keywords = keywords
    if category == "part-time":
        base_keywords += " part time casual student"
    elif category == "professional":
        base_keywords += " IT professional"
    elif category == "aged-care":
        base_keywords = "aged care " + base_keywords
    url = f"https://www.ethicaljobs.com.au/jobs?keywords={base_keywords.replace(' ', '+')}&location={location.replace(' ', '+')}"
    soup = scroll_and_get_source(driver, url, 2)
    jobs = []
    for job in soup.find_all("div", class_="job"):
        try:
            title = job.find("h3").text.strip()
            link = job.find("a")["href"]
            company = job.find("span", class_="organisation").text.strip()
            loc = job.find("span", class_="location").text.strip()
            posted = job.find("span", class_="date").text.strip() if job.find("span", class_="date") else None
            deadline = None
            jobs.append({"title": title, "company": company, "link": link, "location": loc, "source": "EthicalJobs", "posted_date": posted, "deadline_date": deadline, "status": "new"})
        except Exception:
            continue
    driver.quit()
    return filter_by_radius(jobs, lat, lon, radius_km)

def scrape_backpacker(location, radius_km, keywords, category, lat, lon, city=""):
    driver = get_driver()
    base_keywords = keywords
    if category == "part-time":
        base_keywords += " part time casual student"
    elif category == "professional":
        base_keywords += " IT professional"
    elif category == "aged-care":
        base_keywords = "aged care " + base_keywords
    url = f"https://www.backpackerjobboard.com.au/jobs/{base_keywords.replace(' ', '-')}-in-{location.replace(' ', '-')}"
    soup = scroll_and_get_source(driver, url, 2)
    jobs = []
    for job in soup.find_all("div", class_="job"):
        try:
            title = job.find("h3").text.strip()
            link = job.find("a")["href"]
            company = job.find("span", class_="company").text.strip()
            loc = job.find("span", class_="location").text.strip()
            posted = job.find("span", class_="date").text.strip() if job.find("span", class_="date") else None
            deadline = None
            jobs.append({"title": title, "company": company, "link": link, "location": loc, "source": "Backpacker", "posted_date": posted, "deadline_date": deadline, "status": "new"})
        except Exception:
            continue
    driver.quit()
    return filter_by_radius(jobs, lat, lon, radius_km)

def scrape_medicaljobs(location, radius_km, keywords, category, lat, lon, city=""):
    driver = get_driver()
    base_keywords = keywords
    if category == "part-time":
        base_keywords += " part time casual student"
    elif category == "professional":
        base_keywords += " IT professional"
    elif category == "aged-care":
        base_keywords = "aged care " + base_keywords
    url = f"https://www.medicaljobs.com.au/jobs/{base_keywords.replace(' ', '-')}-in-{location.replace(' ', '-')}"
    soup = scroll_and_get_source(driver, url, 2)
    jobs = []
    for job in soup.find_all("div", class_="job"):
        try:
            title = job.find("h3").text.strip()
            link = job.find("a")["href"]
            company = job.find("span", class_="company").text.strip()
            loc = job.find("span", class_="location").text.strip()
            posted = job.find("span", class_="date").text.strip() if job.find("span", class_="date") else None
            deadline = None
            jobs.append({"title": title, "company": company, "link": link, "location": loc, "source": "MedicalJobs", "posted_date": posted, "deadline_date": deadline, "status": "new"})
        except Exception:
            continue
    driver.quit()
    return filter_by_radius(jobs, lat, lon, radius_km)

def scrape_artshub(location, radius_km, keywords, category, lat, lon, city=""):
    driver = get_driver()
    base_keywords = keywords
    if category == "part-time":
        base_keywords += " part time casual student"
    elif category == "professional":
        base_keywords += " IT professional"
    elif category == "aged-care":
        base_keywords = "aged care " + base_keywords
    url = f"https://www.artshub.com.au/jobs/search?keywords={base_keywords.replace(' ', '+')}&location={location.replace(' ', '+')}"
    soup = scroll_and_get_source(driver, url, 2)
    jobs = []
    for job in soup.find_all("div", class_="job"):
        try:
            title = job.find("h3").text.strip()
            link = job.find("a")["href"]
            company = job.find("span", class_="company").text.strip()
            loc = job.find("span", class_="location").text.strip()
            posted = job.find("span", class_="date").text.strip() if job.find("span", class_="date") else None
            deadline = None
            jobs.append({"title": title, "company": company, "link": link, "location": loc, "source": "ArtsHub", "posted_date": posted, "deadline_date": deadline, "status": "new"})
        except Exception:
            continue
    driver.quit()
    return filter_by_radius(jobs, lat, lon, radius_km)

def scrape_flexcareers(location, radius_km, keywords, category, lat, lon, city=""):
    driver = get_driver()
    base_keywords = keywords
    if category == "part-time":
        base_keywords += " part time casual student"
    elif category == "professional":
        base_keywords += " IT professional"
    elif category == "aged-care":
        base_keywords = "aged care " + base_keywords
    url = f"https://www.flexcareers.com.au/jobs/search?keywords={base_keywords.replace(' ', '+')}&location={location.replace(' ', '+')}"
    soup = scroll_and_get_source(driver, url, 2)
    jobs = []
    for job in soup.find_all("div", class_="job"):
        try:
            title = job.find("h3").text.strip()
            link = job.find("a")["href"]
            company = job.find("span", class_="company").text.strip()
            loc = job.find("span", class_="location").text.strip()
            posted = job.find("span", class_="date").text.strip() if job.find("span", class_="date") else None
            deadline = None
            jobs.append({"title": title, "company": company, "link": link, "location": loc, "source": "FlexCareers", "posted_date": posted, "deadline_date": deadline, "status": "new"})
        except Exception:
            continue
    driver.quit()
    return filter_by_radius(jobs, lat, lon, radius_km)

def scrape_gradconnection(location, radius_km, keywords, category, lat, lon, city=""):
    driver = get_driver()
    base_keywords = keywords
    if category == "part-time":
        base_keywords += " part time casual student"
    elif category == "professional":
        base_keywords += " IT professional"
    elif category == "aged-care":
        base_keywords = "aged care " + base_keywords
    url = f"https://au.gradconnection.com/jobs/search?keywords={base_keywords.replace(' ', '+')}&location={location.replace(' ', '+')}"
    soup = scroll_and_get_source(driver, url, 2)
    jobs = []
    for job in soup.find_all("div", class_="job"):
        try:
            title = job.find("h3").text.strip()
            link = job.find("a")["href"]
            company = job.find("span", class_="company").text.strip()
            loc = job.find("span", class_="location").text.strip()
            posted = job.find("span", class_="date").text.strip() if job.find("span", class_="date") else None
            deadline = None
            jobs.append({"title": title, "company": company, "link": link, "location": loc, "source": "GradConnection", "posted_date": posted, "deadline_date": deadline, "status": "new"})
        except Exception:
            continue
    driver.quit()
    return filter_by_radius(jobs, lat, lon, radius_km)

def scrape_probono(location, radius_km, keywords, category, lat, lon, city=""):
    driver = get_driver()
    base_keywords = keywords
    if category == "part-time":
        base_keywords += " part time casual student"
    elif category == "professional":
        base_keywords += " IT professional"
    elif category == "aged-care":
        base_keywords = "aged care " + base_keywords
    url = f"https://probonoaustralia.com.au/jobs/search?keywords={base_keywords.replace(' ', '+')}&location={location.replace(' ', '+')}"
    soup = scroll_and_get_source(driver, url, 2)
    jobs = []
    for job in soup.find_all("div", class_="job"):
        try:
            title = job.find("h3").text.strip()
            link = job.find("a")["href"]
            company = job.find("span", class_="company").text.strip()
            loc = job.find("span", class_="location").text.strip()
            posted = job.find("span", class_="date").text.strip() if job.find("span", class_="date") else None
            deadline = None
            jobs.append({"title": title, "company": company, "link": link, "location": loc, "source": "ProBono", "posted_date": posted, "deadline_date": deadline, "status": "new"})
        except Exception:
            continue
    driver.quit()
    return filter_by_radius(jobs, lat, lon, radius_km)

def scrape_workfast(location, radius_km, keywords, category, lat, lon, city=""):
    driver = get_driver()
    base_keywords = keywords
    if category == "part-time":
        base_keywords += " part time casual student"
    elif category == "professional":
        base_keywords += " IT professional"
    elif category == "aged-care":
        base_keywords = "aged care " + base_keywords
    url = f"https://www.workfast.com.au/jobs/search?keywords={base_keywords.replace(' ', '+')}&location={location.replace(' ', '+')}"
    soup = scroll_and_get_source(driver, url, 2)
    jobs = []
    for job in soup.find_all("div", class_="job"):
        try:
            title = job.find("h3").text.strip()
            link = job.find("a")["href"]
            company = job.find("span", class_="company").text.strip()
            loc = job.find("span", class_="location").text.strip()
            posted = job.find("span", class_="date").text.strip() if job.find("span", class_="date") else None
            deadline = None
            jobs.append({"title": title, "company": company, "link": link, "location": loc, "source": "Workfast", "posted_date": posted, "deadline_date": deadline, "status": "new"})
        except Exception:
            continue
    driver.quit()
    return filter_by_radius(jobs, lat, lon, radius_km)

def scrape_talent(location, radius_km, keywords, category, lat, lon, city=""):
    driver = get_driver()
    base_keywords = keywords
    if category == "part-time":
        base_keywords += " part time casual student"
    elif category == "professional":
        base_keywords += " IT professional"
    elif category == "aged-care":
        base_keywords = "aged care " + base_keywords
    url = f"https://au.talent.com/jobs?keywords={base_keywords.replace(' ', '+')}&location={location.replace(' ', '+')}"
    soup = scroll_and_get_source(driver, url, 2)
    jobs = []
    for job in soup.find_all("div", class_="job"):
        try:
            title = job.find("h3").text.strip()
            link = job.find("a")["href"]
            company = job.find("span", class_="company").text.strip()
            loc = job.find("span", class_="location").text.strip()
            posted = job.find("span", class_="date").text.strip() if job.find("span", class_="date") else None
            deadline = None
            jobs.append({"title": title, "company": company, "link": link, "location": loc, "source": "Talent", "posted_date": posted, "deadline_date": deadline, "status": "new"})
        except Exception:
            continue
    driver.quit()
    return filter_by_radius(jobs, lat, lon, radius_km)

def scrape_applynow(location, radius_km, keywords, category, lat, lon, city=""):
    driver = get_driver()
    base_keywords = keywords
    if category == "part-time":
        base_keywords += " part time casual student"
    elif category == "professional":
        base_keywords += " IT professional"
    elif category == "aged-care":
        base_keywords = "aged care " + base_keywords
    url = f"https://www.applynow.com.au/jobs/search?keywords={base_keywords.replace(' ', '+')}&location={location.replace(' ', '+')}"
    soup = scroll_and_get_source(driver, url, 2)
    jobs = []
    for job in soup.find_all("div", class_="job"):
        try:
            title = job.find("h3").text.strip()
            link = job.find("a")["href"]
            company = job.find("span", class_="company").text.strip()
            loc = job.find("span", class_="location").text.strip()
            posted = job.find("span", class_="date").text.strip() if job.find("span", class_="date") else None
            deadline = None
            jobs.append({"title": title, "company": company, "link": link, "location": loc, "source": "ApplyNow", "posted_date": posted, "deadline_date": deadline, "status": "new"})
        except Exception:
            continue
    driver.quit()
    return filter_by_radius(jobs, lat, lon, radius_km)

def scrape_simplyhired(location, radius_km, keywords, category, lat, lon, city=""):
    driver = get_driver()
    base_keywords = keywords
    if category == "part-time":
        base_keywords += " part time casual student"
    elif category == "professional":
        base_keywords += " IT professional"
    elif category == "aged-care":
        base_keywords = "aged care " + base_keywords
    url = f"https://www.simplyhired.com.au/search?q={base_keywords.replace(' ', '+')}&l={location.replace(' ', '+')}"
    soup = scroll_and_get_source(driver, url, 2)
    jobs = []
    for job in soup.find_all("div", class_="job"):
        try:
            title = job.find("h3").text.strip()
            link = job.find("a")["href"]
            company = job.find("span", class_="company").text.strip()
            loc = job.find("span", class_="location").text.strip()
            posted = job.find("span", class_="date").text.strip() if job.find("span", class_="date") else None
            deadline = None
            jobs.append({"title": title, "company": company, "link": link, "location": loc, "source": "SimplyHired", "posted_date": posted, "deadline_date": deadline, "status": "new"})
        except Exception:
            continue
    driver.quit()
    return filter_by_radius(jobs, lat, lon, radius_km)

def scrape_nrmjobs(location, radius_km, keywords, category, lat, lon, city=""):
    driver = get_driver()
    base_keywords = keywords
    if category == "part-time":
        base_keywords += " part time casual student"
    elif category == "professional":
        base_keywords += " IT professional"
    elif category == "aged-care":
        base_keywords = "aged care " + base_keywords
    url = f"https://www.nrmjobs.com.au/jobs/search?keywords={base_keywords.replace(' ', '+')}&location={location.replace(' ', '+')}"
    soup = scroll_and_get_source(driver, url, 2)
    jobs = []
    for job in soup.find_all("div", class_="job"):
        try:
            title = job.find("h3").text.strip()
            link = job.find("a")["href"]
            company = job.find("span", class_="company").text.strip()
            loc = job.find("span", class_="location").text.strip()
            posted = job.find("span", class_="date").text.strip() if job.find("span", class_="date") else None
            deadline = None
            jobs.append({"title": title, "company": company, "link": link, "location": loc, "source": "NRMJobs", "posted_date": posted, "deadline_date": deadline, "status": "new"})
        except Exception:
            continue
    driver.quit()
    return filter_by_radius(jobs, lat, lon, radius_km)

def scrape_careerjet(location, radius_km, keywords, category, lat, lon, city=""):
    driver = get_driver()
    base_keywords = keywords
    if category == "part-time":
        base_keywords += " part time casual student"
    elif category == "professional":
        base_keywords += " IT professional"
    elif category == "aged-care":
        base_keywords = "aged care " + base_keywords
    url = f"https://www.careerjet.com.au/search/jobs?s={base_keywords.replace(' ', '+')}&l={location.replace(' ', '+')}"
    soup = scroll_and_get_source(driver, url, 2)
    jobs = []
    for job in soup.find_all("div", class_="job"):
        try:
            title = job.find("h3").text.strip()
            link = job.find("a")["href"]
            company = job.find("span", class_="company").text.strip()
            loc = job.find("span", class_="location").text.strip()
            posted = job.find("span", class_="date").text.strip() if job.find("span", class_="date") else None
            deadline = None
            jobs.append({"title": title, "company": company, "link": link, "location": loc, "source": "CareerJet", "posted_date": posted, "deadline_date": deadline, "status": "new"})
        except Exception:
            continue
    driver.quit()
    return filter_by_radius(jobs, lat, lon, radius_km)

def scrape_grabjobs(location, radius_km, keywords, category, lat, lon, city=""):
    driver = get_driver()
    base_keywords = keywords
    if category == "part-time":
        base_keywords += " part time casual student"
    elif category == "professional":
        base_keywords += " IT professional"
    elif category == "aged-care":
        base_keywords = "aged care " + base_keywords
    url = f"https://grabjobs.co/au/jobs?keywords={base_keywords.replace(' ', '+')}&location={location.replace(' ', '+')}"
    soup = scroll_and_get_source(driver, url, 2)
    jobs = []
    for job in soup.find_all("div", class_="job"):
        try:
            title = job.find("h3").text.strip()
            link = job.find("a")["href"]
            company = job.find("span", class_="company").text.strip()
            loc = job.find("span", class_="location").text.strip()
            posted = job.find("span", class_="date").text.strip() if job.find("span", class_="date") else None
            deadline = None
            jobs.append({"title": title, "company": company, "link": link, "location": loc, "source": "GrabJobs", "posted_date": posted, "deadline_date": deadline, "status": "new"})
        except Exception:
            continue
    driver.quit()
    return filter_by_radius(jobs, lat, lon, radius_km)

def scrape_facebook_jobs(location, radius_km, keywords, category, lat, lon, city):
    driver = get_driver()
    base_keywords = keywords
    if category == "part-time":
        base_keywords += " part time casual student"
    elif category == "professional":
        base_keywords += " IT professional"
    elif category == "aged-care":
        base_keywords = "aged care " + base_keywords
    url = f"https://www.facebook.com/marketplace/{city.replace(' ', '-')}/jobs?query={base_keywords.replace(' ', '+')}&radius={radius_km}"
    soup = scroll_and_get_source(driver, url, 4)
    jobs = []
    for job in soup.find_all("div", class_="x9f619"):
        try:
            title = job.find("span", class_="x1lliihq").text.strip()
            link = "https://www.facebook.com" + job.find("a")["href"]
            company = "Facebook User"
            loc = location
            posted = None
            deadline = None
            jobs.append({"title": title, "company": company, "link": link, "location": loc, "source": "Facebook", "posted_date": posted, "deadline_date": deadline, "status": "new"})
        except Exception:
            continue
    driver.quit()
    return filter_by_radius(jobs, lat, lon, radius_km)

def scrape_instagram_jobs(location, radius_km, keywords, category, lat, lon, city=""):
    driver = get_driver()
    base_keywords = keywords
    if category == "part-time":
        base_keywords += " part time casual student"
    elif category == "professional":
        base_keywords += " IT professional"
    elif category == "aged-care":
        base_keywords = "aged care " + base_keywords
    url = f"https://www.instagram.com/explore/search/keyword/?q={base_keywords.replace(' ', '%20')}%20jobs%20{location.replace(' ', '%20')}"
    soup = scroll_and_get_source(driver, url, 5)
    jobs = []
    for job in soup.find_all("div", class_="x9f619"):
        try:
            title = job.find("span", class_="x1lliihq").text.strip()
            link = "https://www.instagram.com" + job.find("a")["href"]
            company = "Instagram User"
            loc = location
            posted = None
            deadline = None
            jobs.append({"title": title, "company": company, "link": link, "location": loc, "source": "Instagram", "posted_date": posted, "deadline_date": deadline, "status": "new"})
        except Exception:
            continue
    driver.quit()
    return filter_by_radius(jobs, lat, lon, radius_km)

def scrape_tiktok_jobs(location, radius_km, keywords, category, lat, lon, city=""):
    driver = get_driver()
    base_keywords = keywords
    if category == "part-time":
        base_keywords += " part time casual student"
    elif category == "professional":
        base_keywords += " IT professional"
    elif category == "aged-care":
        base_keywords = "aged care " + base_keywords
    url = f"https://www.tiktok.com/search?q={base_keywords.replace(' ', '%20')}%20jobs%20{location.replace(' ', '%20')}"
    soup = scroll_and_get_source(driver, url, 5)
    jobs = []
    for job in soup.find_all("div", class_="tiktok-1qd04g-DivItemContainerV2"):
        try:
            title = job.find("div", class_="tiktok-1p23jpt-DivText").text.strip()
            link = "https://www.tiktok.com" + job.find("a")["href"]
            company = "TikTok User"
            loc = location
            posted = None
            deadline = None
            jobs.append({"title": title, "company": company, "link": link, "location": loc, "source": "TikTok", "posted_date": posted, "deadline_date": deadline, "status": "new"})
        except Exception:
            continue
    driver.quit()
    return filter_by_radius(jobs, lat, lon, radius_km)

def scrape_custom(url, category, city=""):
    driver = get_driver()
    soup = scroll_and_get_source(driver, url, 2)
    jobs = []
    for job in soup.find_all("div", class_="post") or soup.find_all("li", class_="item"):
        try:
            title = job.find("h2") or job.find("a")
            title = title.text.strip() if title else "N/A"
            link = job.find("a")["href"] if job.find("a") else url
            company = job.find("span", class_="company") or job.find("div", class_="employer")
            company = company.text.strip() if company else "N/A"
            loc = job.find("span", class_="location") or "N/A"
            loc = loc.text.strip() if loc else "N/A"
            posted = job.find("time") or job.find("span", class_="date")
            posted = posted.get("datetime") or posted.text.strip() if posted else None
            deadline = job.find("span", class_="deadline") or None
            deadline = deadline.text.strip() if deadline else None
            jobs.append({"title": title, "company": company, "link": link, "location": loc, "source": "Custom", "posted_date": posted, "deadline_date": deadline, "status": "new"})
        except Exception:
            continue
    driver.quit()
    return jobs

def scrape_jobs(location, radius_km, keywords, category, lat, lon, city, custom_url=""):
    all_jobs = []
    site_functions = [
        (scrape_seek, "Seek"),
        # (scrape_indeed, "Indeed"),
        # (scrape_jora, "Jora"),
        # (scrape_linkedin, "LinkedIn"),
        # (scrape_glassdoor, "Glassdoor"),
        # (scrape_careerone, "CareerOne"),
        # (scrape_adzuna, "Adzuna"),
        # (scrape_apsjobs, "APSJobs"),
        # (scrape_jobsvic, "JobsVIC"),
        # (scrape_smartjobs, "SmartJobs"),
        # (scrape_jobswa, "JobsWA"),
        # (scrape_ethicaljobs, "EthicalJobs"),
        # (scrape_backpacker, "Backpacker"),
        # (scrape_medicaljobs, "MedicalJobs"),
        # (scrape_artshub, "ArtsHub"),
        # (scrape_flexcareers, "FlexCareers"),
        # (scrape_gradconnection, "GradConnection"),
        # (scrape_probono, "ProBono"),
        # (scrape_workfast, "Workfast"),
        # (scrape_talent, "Talent"),
        # (scrape_applynow, "ApplyNow"),
        # (scrape_simplyhired, "SimplyHired"),
        # (scrape_nrmjobs, "NRMJobs"),
        # (scrape_careerjet, "CareerJet"),
        # (scrape_grabjobs, "GrabJobs"),
        # (scrape_facebook_jobs, "Facebook"),
        # (scrape_instagram_jobs, "Instagram"),
        # (scrape_tiktok_jobs, "TikTok"),
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