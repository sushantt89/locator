from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import time
from bs4 import BeautifulSoup
from geocode import filter_by_radius, get_coordinates

def get_driver():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("user-agent=LocatorApp/1.0")
    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=options)

def scroll_and_get_source(driver, url, scrolls=3):
    try:
        driver.get(url)
        time.sleep(5)
        for _ in range(scrolls):
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(3)
        return BeautifulSoup(driver.page_source, "html.parser")
    except Exception as e:
        print(f"Error accessing {url}: {e}")
        return BeautifulSoup("", "html.parser")

def scrape_domain(location, radius_km, lat, lon):
    driver = get_driver()
    url = f"https://www.domain.com.au/rent/{location.replace(' ', '-')}-nsw-2000/?distance={radius_km}"
    soup = scroll_and_get_source(driver, url, 2)
    listings = []
    for item in soup.find_all("li", class_="search-results__listing"):
        try:
            title = item.find("h2").text.strip()
            link = item.find("a")["href"]
            price = item.find("p", class_="listing-result__price").text.strip()
            loc = item.find("span", class_="listing-result__address").text.strip()
            posted = item.find("span", class_="listing-result__listed-date").text.strip() if item.find("span", class_="listing-result__listed-date") else None
            deadline = None
            listings.append({"title": title, "price": price, "link": link, "location": loc, "source": "Domain", "posted_date": posted, "deadline_date": deadline, "status": "new"})
        except Exception:
            continue
    driver.quit()
    return filter_by_radius(listings, lat, lon, radius_km)

def scrape_realestate(location, radius_km, lat, lon):
    driver = get_driver()
    url = f"https://www.realestate.com.au/rent/in-{location.replace(' ', '%20')}/list-1?distance={radius_km}"
    soup = scroll_and_get_source(driver, url, 2)
    listings = []
    for item in soup.find_all("div", class_="residential-card__content"):
        try:
            title = item.find("h2", class_="residential-card__address-heading").text.strip()
            link = "https://www.realestate.com.au" + item.find("a")["href"]
            price = item.find("span", class_="property-price").text.strip()
            loc = item.find("span", class_="residential-card__address-street").text.strip()
            posted = None
            deadline = None
            listings.append({"title": title, "price": price, "link": link, "location": loc, "source": "Realestate", "posted_date": posted, "deadline_date": deadline, "status": "new"})
        except Exception:
            continue
    driver.quit()
    return filter_by_radius(listings, lat, lon, radius_km)

def scrape_gumtree(location, radius_km, lat, lon):
    driver = get_driver()
    url = f"https://www.gumtree.com.au/s-flats-houses/{location.replace(' ', '-')}/c18294l3003435?distance={radius_km}"
    soup = scroll_and_get_source(driver, url, 2)
    listings = []
    for item in soup.find_all("div", class_="user-ad-collection-new-design__wrapper--row"):
        try:
            title = item.find("a", class_="user-ad-row-new-design__title").text.strip()
            link = "https://www.gumtree.com.au" + item.find("a")["href"]
            price = item.find("span", class_="user-ad-price-new-design__price").text.strip()
            loc = item.find("span", class_="user-ad-row-new-design__location").text.strip()
            posted = item.find("span", class_="user-ad-row-new-design__posted").text.strip() if item.find("span", class_="user-ad-row-new-design__posted") else None
            deadline = None
            listings.append({"title": title, "price": price, "link": link, "location": loc, "source": "Gumtree", "posted_date": posted, "deadline_date": deadline, "status": "new"})
        except Exception:
            continue
    driver.quit()
    return filter_by_radius(listings, lat, lon, radius_km)

def scrape_airbnb(location, radius_km, lat, lon):
    driver = get_driver()
    url = f"https://www.airbnb.com.au/s/{location.replace(' ', '-')}/homes?distance={radius_km}"
    soup = scroll_and_get_source(driver, url, 2)
    listings = []
    for item in soup.find_all("div", class_="c4mnd7m"):
        try:
            title = item.find("div", class_="t1jojoys").text.strip()
            link = "https://www.airbnb.com" + item.find("a")["href"]
            price = item.find("span", class_="_tyxjp1").text.strip()
            loc = location
            posted = None
            deadline = None
            listings.append({"title": title, "price": price, "link": link, "location": loc, "source": "Airbnb", "posted_date": posted, "deadline_date": deadline, "status": "new"})
        except Exception:
            continue
    driver.quit()
    return filter_by_radius(listings, lat, lon, radius_km)

def scrape_flatmates(location, radius_km, lat, lon):
    driver = get_driver()
    url = f"https://flatmates.com.au/rooms/{location.replace(' ', '-')}"
    soup = scroll_and_get_source(driver, url, 2)
    listings = []
    for item in soup.find_all("div", class_="listing-card"):
        try:
            title = item.find("h3", class_="listing-card-title").text.strip()
            link = "https://flatmates.com.au" + item.find("a")["href"]
            price = item.find("div", class_="price").text.strip()
            loc = item.find("div", class_="location").text.strip()
            posted = item.find("div", class_="posted").text.strip() if item.find("div", class_="posted") else None
            deadline = None
            listings.append({"title": title, "price": price, "link": link, "location": loc, "source": "Flatmates", "posted_date": posted, "deadline_date": deadline, "status": "new"})
        except Exception:
            continue
    driver.quit()
    return filter_by_radius(listings, lat, lon, radius_km)

def scrape_booking(location, radius_km, lat, lon):
    driver = get_driver()
    url = f"https://www.booking.com/searchresults.html?ss={location.replace(' ', '+')}"
    soup = scroll_and_get_source(driver, url, 2)
    listings = []
    for item in soup.find_all("div", class_="c1edfd8c4a"):
        try:
            title = item.find("div", class_="fcab3ed991").text.strip()
            link = item.find("a")["href"]
            price = item.find("span", class_="fcab3ed991").text.strip()
            loc = location
            posted = None
            deadline = None
            listings.append({"title": title, "price": price, "link": link, "location": loc, "source": "Booking", "posted_date": posted, "deadline_date": deadline, "status": "new"})
        except Exception:
            continue
    driver.quit()
    return filter_by_radius(listings, lat, lon, radius_km)

def scrape_stayz(location, radius_km, lat, lon):
    driver = get_driver()
    url = f"https://www.stayz.com.au/holiday-rental/australia/{location.replace(' ', '-')}"
    soup = scroll_and_get_source(driver, url, 2)
    listings = []
    for item in soup.find_all("div", class_="listing"):
        try:
            title = item.find("h3").text.strip()
            link = item.find("a")["href"]
            price = item.find("span", class_="price").text.strip()
            loc = item.find("span", class_="location").text.strip()
            posted = None
            deadline = None
            listings.append({"title": title, "price": price, "link": link, "location": loc, "source": "Stayz", "posted_date": posted, "deadline_date": deadline, "status": "new"})
        except Exception:
            continue
    driver.quit()
    return filter_by_radius(listings, lat, lon, radius_km)

def scrape_rent(location, radius_km, lat, lon):
    driver = get_driver()
    url = f"https://www.rent.com.au/properties/{location.replace(' ', '-')}"
    soup = scroll_and_get_source(driver, url, 2)
    listings = []
    for item in soup.find_all("div", class_="property-card"):
        try:
            title = item.find("h3").text.strip()
            link = item.find("a")["href"]
            price = item.find("span", class_="price").text.strip()
            loc = item.find("span", class_="location").text.strip()
            posted = None
            deadline = None
            listings.append({"title": title, "price": price, "link": link, "location": loc, "source": "Rent.com.au", "posted_date": posted, "deadline_date": deadline, "status": "new"})
        except Exception:
            continue
    driver.quit()
    return filter_by_radius(listings, lat, lon, radius_km)

def scrape_allhomes(location, radius_km, lat, lon):
    driver = get_driver()
    url = f"https://www.allhomes.com.au/rent/{location.replace(' ', '-')}"
    soup = scroll_and_get_source(driver, url, 2)
    listings = []
    for item in soup.find_all("div", class_="property-listing"):
        try:
            title = item.find("h2").text.strip()
            link = item.find("a")["href"]
            price = item.find("span", class_="price").text.strip()
            loc = item.find("span", class_="address").text.strip()
            posted = None
            deadline = None
            listings.append({"title": title, "price": price, "link": link, "location": loc, "source": "Allhomes", "posted_date": posted, "deadline_date": deadline, "status": "new"})
        except Exception:
            continue
    driver.quit()
    return filter_by_radius(listings, lat, lon, radius_km)

def scrape_homely(location, radius_km, lat, lon):
    driver = get_driver()
    url = f"https://www.homely.com.au/rent/{location.replace(' ', '-')}"
    soup = scroll_and_get_source(driver, url, 2)
    listings = []
    for item in soup.find_all("div", class_="listing"):
        try:
            title = item.find("h3").text.strip()
            link = item.find("a")["href"]
            price = item.find("span", class_="price").text.strip()
            loc = item.find("span", class_="location").text.strip()
            posted = None
            deadline = None
            listings.append({"title": title, "price": price, "link": link, "location": loc, "source": "Homely", "posted_date": posted, "deadline_date": deadline, "status": "new"})
        except Exception:
            continue
    driver.quit()
    return filter_by_radius(listings, lat, lon, radius_km)

def scrape_holidu(location, radius_km, lat, lon):
    driver = get_driver()
    url = f"https://www.holidu.com.au/s/{location.replace(' ', '-')}"
    soup = scroll_and_get_source(driver, url, 2)
    listings = []
    for item in soup.find_all("div", class_="listing-card"):
        try:
            title = item.find("h3").text.strip()
            link = item.find("a")["href"]
            price = item.find("span", class_="price").text.strip()
            loc = location
            posted = None
            deadline = None
            listings.append({"title": title, "price": price, "link": link, "location": loc, "source": "Holidu", "posted_date": posted, "deadline_date": deadline, "status": "new"})
        except Exception:
            continue
    driver.quit()
    return filter_by_radius(listings, lat, lon, radius_km)

def scrape_cozycozy(location, radius_km, lat, lon):
    driver = get_driver()
    url = f"https://www.cozycozy.com/au/{location.replace(' ', '-')}"
    soup = scroll_and_get_source(driver, url, 2)
    listings = []
    for item in soup.find_all("div", class_="accommodation-card"):
        try:
            title = item.find("h2").text.strip()
            link = item.find("a")["href"]
            price = item.find("span", class_="price").text.strip()
            loc = location
            posted = None
            deadline = None
            listings.append({"title": title, "price": price, "link": link, "location": loc, "source": "Cozycozy", "posted_date": posted, "deadline_date": deadline, "status": "new"})
        except Exception:
            continue
    driver.quit()
    return filter_by_radius(listings, lat, lon, radius_km)

def scrape_vrbo(location, radius_km, lat, lon):
    driver = get_driver()
    url = f"https://www.vrbo.com/en-au/search/{location.replace(' ', '-')}"
    soup = scroll_and_get_source(driver, url, 2)
    listings = []
    for item in soup.find_all("div", class_="listing"):
        try:
            title = item.find("h3").text.strip()
            link = item.find("a")["href"]
            price = item.find("span", class_="price").text.strip()
            loc = location
            posted = None
            deadline = None
            listings.append({"title": title, "price": price, "link": link, "location": loc, "source": "Vrbo", "posted_date": posted, "deadline_date": deadline, "status": "new"})
        except Exception:
            continue
    driver.quit()
    return filter_by_radius(listings, lat, lon, radius_km)

def scrape_expedia(location, radius_km, lat, lon):
    driver = get_driver()
    url = f"https://www.expedia.com.au/Hotels/{location.replace(' ', '-')}"
    soup = scroll_and_get_source(driver, url, 2)
    listings = []
    for item in soup.find_all("div", class_="hotel-card"):
        try:
            title = item.find("h3").text.strip()
            link = item.find("a")["href"]
            price = item.find("span", class_="price").text.strip()
            loc = location
            posted = None
            deadline = None
            listings.append({"title": title, "price": price, "link": link, "location": loc, "source": "Expedia", "posted_date": posted, "deadline_date": deadline, "status": "new"})
        except Exception:
            continue
    driver.quit()
    return filter_by_radius(listings, lat, lon, radius_km)

def scrape_agoda(location, radius_km, lat, lon):
    driver = get_driver()
    url = f"https://www.agoda.com/hotels/{location.replace(' ', '-')}"
    soup = scroll_and_get_source(driver, url, 2)
    listings = []
    for item in soup.find_all("div", class_="hotel-listing"):
        try:
            title = item.find("h3").text.strip()
            link = item.find("a")["href"]
            price = item.find("span", class_="price").text.strip()
            loc = location
            posted = None
            deadline = None
            listings.append({"title": title, "price": price, "link": link, "location": loc, "source": "Agoda", "posted_date": posted, "deadline_date": deadline, "status": "new"})
        except Exception:
            continue
    driver.quit()
    return filter_by_radius(listings, lat, lon, radius_km)

def scrape_wotif(location, radius_km, lat, lon):
    driver = get_driver()
    url = f"https://www.wotif.com/Hotels/{location.replace(' ', '-')}"
    soup = scroll_and_get_source(driver, url, 2)
    listings = []
    for item in soup.find_all("div", class_="hotel-card"):
        try:
            title = item.find("h3").text.strip()
            link = item.find("a")["href"]
            price = item.find("span", class_="price").text.strip()
            loc = location
            posted = None
            deadline = None
            listings.append({"title": title, "price": price, "link": link, "location": loc, "source": "Wotif", "posted_date": posted, "deadline_date": deadline, "status": "new"})
        except Exception:
            continue
    driver.quit()
    return filter_by_radius(listings, lat, lon, radius_km)

def scrape_hostelworld(location, radius_km, lat, lon):
    driver = get_driver()
    url = f"https://www.hostelworld.com/search?city={location.replace(' ', '-')}"
    soup = scroll_and_get_source(driver, url, 2)
    listings = []
    for item in soup.find_all("div", class_="property-card"):
        try:
            title = item.find("h2").text.strip()
            link = item.find("a")["href"]
            price = item.find("span", class_="price").text.strip()
            loc = location
            posted = None
            deadline = None
            listings.append({"title": title, "price": price, "link": link, "location": loc, "source": "Hostelworld", "posted_date": posted, "deadline_date": deadline, "status": "new"})
        except Exception:
            continue
    driver.quit()
    return filter_by_radius(listings, lat, lon, radius_km)

def scrape_luxuryescapes(location, radius_km, lat, lon):
    driver = get_driver()
    url = f"https://www.luxuryescapes.com/au/hotels/{location.replace(' ', '-')}"
    soup = scroll_and_get_source(driver, url, 2)
    listings = []
    for item in soup.find_all("div", class_="hotel-card"):
        try:
            title = item.find("h3").text.strip()
            link = item.find("a")["href"]
            price = item.find("span", class_="price").text.strip()
            loc = location
            posted = None
            deadline = None
            listings.append({"title": title, "price": price, "link": link, "location": loc, "source": "LuxuryEscapes", "posted_date": posted, "deadline_date": deadline, "status": "new"})
        except Exception:
            continue
    driver.quit()
    return filter_by_radius(listings, lat, lon, radius_km)

def scrape_trivago(location, radius_km, lat, lon):
    driver = get_driver()
    url = f"https://www.trivago.com.au/search?search={location.replace(' ', '-')}"
    soup = scroll_and_get_source(driver, url, 2)
    listings = []
    for item in soup.find_all("div", class_="hotel-item"):
        try:
            title = item.find("h3").text.strip()
            link = item.find("a")["href"]
            price = item.find("span", class_="price").text.strip()
            loc = location
            posted = None
            deadline = None
            listings.append({"title": title, "price": price, "link": link, "location": loc, "source": "Trivago", "posted_date": posted, "deadline_date": deadline, "status": "new"})
        except Exception:
            continue
    driver.quit()
    return filter_by_radius(listings, lat, lon, radius_km)

def scrape_tripadvisor(location, radius_km, lat, lon):
    driver = get_driver()
    url = f"https://www.tripadvisor.com.au/Hotels-{location.replace(' ', '-')}"
    soup = scroll_and_get_source(driver, url, 2)
    listings = []
    for item in soup.find_all("div", class_="listing"):
        try:
            title = item.find("h3").text.strip()
            link = item.find("a")["href"]
            price = item.find("span", class_="price").text.strip()
            loc = location
            posted = None
            deadline = None
            listings.append({"title": title, "price": price, "link": link, "location": loc, "source": "Tripadvisor", "posted_date": posted, "deadline_date": deadline, "status": "new"})
        except Exception:
            continue
    driver.quit()
    return filter_by_radius(listings, lat, lon, radius_km)

def scrape_airkeeper(location, radius_km, lat, lon):
    driver = get_driver()
    url = f"https://www.airkeeper.com.au/properties/{location.replace(' ', '-')}"
    soup = scroll_and_get_source(driver, url, 2)
    listings = []
    for item in soup.find_all("div", class_="property-card"):
        try:
            title = item.find("h3").text.strip()
            link = item.find("a")["href"]
            price = item.find("span", class_="price").text.strip()
            loc = location
            posted = None
            deadline = None
            listings.append({"title": title, "price": price, "link": link, "location": loc, "source": "Airkeeper", "posted_date": posted, "deadline_date": deadline, "status": "new"})
        except Exception:
            continue
    driver.quit()
    return filter_by_radius(listings, lat, lon, radius_km)

def scrape_madecomfy(location, radius_km, lat, lon):
    driver = get_driver()
    url = f"https://www.madecomfy.com.au/properties/{location.replace(' ', '-')}"
    soup = scroll_and_get_source(driver, url, 2)
    listings = []
    for item in soup.find_all("div", class_="listing"):
        try:
            title = item.find("h3").text.strip()
            link = item.find("a")["href"]
            price = item.find("span", class_="price").text.strip()
            loc = location
            posted = None
            deadline = None
            listings.append({"title": title, "price": price, "link": link, "location": loc, "source": "MadeComfy", "posted_date": posted, "deadline_date": deadline, "status": "new"})
        except Exception:
            continue
    driver.quit()
    return filter_by_radius(listings, lat, lon, radius_km)

def scrape_vaquay(location, radius_km, lat, lon):
    driver = get_driver()
    url = f"https://www.vaquay.com/properties/{location.replace(' ', '-')}"
    soup = scroll_and_get_source(driver, url, 2)
    listings = []
    for item in soup.find_all("div", class_="property-card"):
        try:
            title = item.find("h3").text.strip()
            link = item.find("a")["href"]
            price = item.find("span", class_="price").text.strip()
            loc = location
            posted = None
            deadline = None
            listings.append({"title": title, "price": price, "link": link, "location": loc, "source": "Vaquay", "posted_date": posted, "deadline_date": deadline, "status": "new"})
        except Exception:
            continue
    driver.quit()
    return filter_by_radius(listings, lat, lon, radius_km)

def scrape_kozyguru(location, radius_km, lat, lon):
    driver = get_driver()
    url = f"https://www.kozyguru.com.au/properties/{location.replace(' ', '-')}"
    soup = scroll_and_get_source(driver, url, 2)
    listings = []
    for item in soup.find_all("div", class_="listing"):
        try:
            title = item.find("h3").text.strip()
            link = item.find("a")["href"]
            price = item.find("span", class_="price").text.strip()
            loc = location
            posted = None
            deadline = None
            listings.append({"title": title, "price": price, "link": link, "location": loc, "source": "KozyGuru", "posted_date": posted, "deadline_date": deadline, "status": "new"})
        except Exception:
            continue
    driver.quit()
    return filter_by_radius(listings, lat, lon, radius_km)

def scrape_uhomes(location, radius_km, lat, lon):
    driver = get_driver()
    url = f"https://www.uhomes.com/au/{location.replace(' ', '-')}/apartments"
    soup = scroll_and_get_source(driver, url, 2)
    listings = []
    for item in soup.find_all("div", class_="apartment-card"):
        try:
            title = item.find("h3").text.strip()
            link = item.find("a")["href"]
            price = item.find("span", class_="price").text.strip()
            loc = location
            posted = None
            deadline = None
            listings.append({"title": title, "price": price, "link": link, "location": loc, "source": "Uhomes", "posted_date": posted, "deadline_date": deadline, "status": "new"})
        except Exception:
            continue
    driver.quit()
    return filter_by_radius(listings, lat, lon, radius_km)

def scrape_facebook_accom(location, radius_km, keywords, lat, lon, city):
    driver = get_driver()
    url = f"https://www.facebook.com/marketplace/{city.replace(' ', '-')}/propertyrentals?query={keywords.replace(' ', '+')}&radius={radius_km}"
    soup = scroll_and_get_source(driver, url, 4)
    listings = []
    for item in soup.find_all("div", class_="x9f619"):
        try:
            title = item.find("span", class_="x1lliihq").text.strip()
            link = "https://www.facebook.com" + item.find("a")["href"]
            price = item.find("span", class_="x193iq5w").text.strip() if item.find("span", class_="x193iq5w") else "N/A"
            loc = location
            posted = None
            deadline = None
            listings.append({"title": title, "price": price, "link": link, "location": loc, "source": "Facebook", "posted_date": posted, "deadline_date": deadline, "status": "new"})
        except Exception:
            continue
    driver.quit()
    return filter_by_radius(listings, lat, lon, radius_km)

def scrape_instagram_accom(location, radius_km, keywords, lat, lon):
    driver = get_driver()
    url = f"https://www.instagram.com/explore/search/keyword/?q={keywords.replace(' ', '%20')}%20rentals%20{location.replace(' ', '%20')}"
    soup = scroll_and_get_source(driver, url, 5)
    listings = []
    for item in soup.find_all("div", class_="x9f619"):
        try:
            title = item.find("span", class_="x1lliihq").text.strip()
            link = "https://www.instagram.com" + item.find("a")["href"]
            price = "N/A"
            loc = location
            posted = None
            deadline = None
            listings.append({"title": title, "price": price, "link": link, "location": loc, "source": "Instagram", "posted_date": posted, "deadline_date": deadline, "status": "new"})
        except Exception:
            continue
    driver.quit()
    return filter_by_radius(listings, lat, lon, radius_km)

def scrape_tiktok_accom(location, radius_km, keywords, lat, lon):
    driver = get_driver()
    url = f"https://www.tiktok.com/search?q={keywords.replace(' ', '%20')}%20rentals%20{location.replace(' ', '%20')}"
    soup = scroll_and_get_source(driver, url, 5)
    listings = []
    for item in soup.find_all("div", class_="tiktok-1qd04g-DivItemContainerV2"):
        try:
            title = item.find("div", class_="tiktok-1p23jpt-DivText").text.strip()
            link = "https://www.tiktok.com" + item.find("a")["href"]
            price = "N/A"
            loc = location
            posted = None
            deadline = None
            listings.append({"title": title, "price": price, "link": link, "location": loc, "source": "TikTok", "posted_date": posted, "deadline_date": deadline, "status": "new"})
        except Exception:
            continue
    driver.quit()
    return filter_by_radius(listings, lat, lon, radius_km)

def scrape_custom_accom(url):
    driver = get_driver()
    soup = scroll_and_get_source(driver, url, 2)
    listings = []
    for item in soup.find_all("div", class_="listing") or soup.find_all("article"):
        try:
            title = item.find("h2") or item.find("h3")
            title = title.text.strip() if title else "N/A"
            link = item.find("a")["href"] if item.find("a") else url
            price = item.find("span", class_="price") or item.find("div", class_="price")
            price = price.text.strip() if price else "N/A"
            loc = item.find("span", class_="location") or item.find("div", class_="location")
            loc = loc.text.strip() if loc else "N/A"
            posted = item.find("time") or item.find("span", class_="date")
            posted = posted.get("datetime") or posted.text.strip() if posted else None
            deadline = None
            listings.append({"title": title, "price": price, "link": link, "location": loc, "source": "Custom", "posted_date": posted, "deadline_date": deadline, "status": "new"})
        except Exception:
            continue
    driver.quit()
    return listings

def scrape_accommodations(location, radius_km, lat, lon, city, custom_url=""):
    all_listings = []
    site_functions = [
        (scrape_domain, "Domain"),
        (scrape_realestate, "Realestate"),
        (scrape_gumtree, "Gumtree"),
        (scrape_airbnb, "Airbnb"),
        (scrape_flatmates, "Flatmates"),
        (scrape_booking, "Booking"),
        (scrape_stayz, "Stayz"),
        (scrape_rent, "Rent.com.au"),
        (scrape_allhomes, "Allhomes"),
        (scrape_homely, "Homely"),
        (scrape_holidu, "Holidu"),
        (scrape_cozycozy, "Cozycozy"),
        (scrape_vrbo, "Vrbo"),
        (scrape_expedia, "Expedia"),
        (scrape_agoda, "Agoda"),
        (scrape_wotif, "Wotif"),
        (scrape_hostelworld, "Hostelworld"),
        (scrape_luxuryescapes, "LuxuryEscapes"),
        (scrape_trivago, "Trivago"),
        (scrape_tripadvisor, "Tripadvisor"),
        (scrape_airkeeper, "Airkeeper"),
        (scrape_madecomfy, "MadeComfy"),
        (scrape_vaquay, "Vaquay"),
        (scrape_kozyguru, "KozyGuru"),
        (scrape_uhomes, "Uhomes"),
        (scrape_facebook_accom, "Facebook"),
        (scrape_instagram_accom, "Instagram"),
        (scrape_tiktok_accom, "TikTok"),
    ]
    total_sites = len(site_functions) + (1 if custom_url else 0)
    for idx, (func, site_name) in enumerate(site_functions):
        yield {"status": f"Scraping {site_name}...", "progress": (idx + 1) / total_sites}
        listings = func(location, radius_km, "rental", lat, lon, city=city) if func in [scrape_facebook_accom, scrape_instagram_accom, scrape_tiktok_accom] else func(location, radius_km, lat, lon)
        all_listings.extend(listings)
    if custom_url:
        yield {"status": "Scraping custom URL...", "progress": 1.0}
        all_listings.extend(scrape_custom_accom(custom_url))
    seen = set()
    unique = []
    for item in all_listings:
        if item["link"] not in seen:
            seen.add(item["link"])
            unique.append(item)
    yield {"status": "Completed", "progress": 1.0, "results": unique}