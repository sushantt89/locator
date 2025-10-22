import streamlit as st
import pandas as pd
from geocode import get_coordinates
from scrapers import scrape_jobs, scrape_accommodations
from database import save_listings, get_listings, update_listing, get_db
import uuid
import logging
import threading
import queue
import time
import urllib.parse

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Set wide layout for full-screen usage
st.set_page_config(layout="wide")

# Custom CSS to remove padding/margins and make tables full-width
st.markdown("""
    <style>
    /* Remove default Streamlit padding */
    .main .block-container {
        padding: 0 !important;
        max-width: 100% !important;
    }
    /* Ensure data editor takes full width */
    .stDataFrame {
        width: 100% !important;
    }
    /* Adjust column filters to fit full width */
    .stColumn {
        padding: 0 5px !important;
    }
    </style>
""", unsafe_allow_html=True)

st.title("Locator - Australia 🇦🇺")

# Define categories and tab names
categories = ["accommodation", "part-time", "professional", "aged-care"]
tab_names = ["Search", "🏠 Rooms/Accommodation", "💼 Part-Time Jobs", "💻 Professional Jobs", "❤️ Aged Care Jobs"]

# Initialize session state for scraping status
if 'scraping_thread' not in st.session_state:
    st.session_state.scraping_thread = None
if 'scraping_complete' not in st.session_state:
    st.session_state.scraping_complete = False
if 'scraping_results' not in st.session_state:
    st.session_state.scraping_results = []
if 'scraping_status' not in st.session_state:
    st.session_state.scraping_status = ""
if 'scraping_progress' not in st.session_state:
    st.session_state.scraping_progress = 0
if 'scraping_error' not in st.session_state:
    st.session_state.scraping_error = None
if 'start_address' not in st.session_state:
    st.session_state.start_address = ""

tabs = st.tabs(tab_names)

def apply_filters(df, filters):
    """Apply filters to the dataframe based on user input."""
    filtered_df = df.copy()
    for column, value in filters.items():
        if value:  # Only apply filter if a value is selected/entered
            if column in ["keyword", "location", "source", "status"]:
                # Exact match for dropdown filters
                filtered_df = filtered_df[filtered_df[column] == value]
            elif column in ["title", "company", "price", "posted_date", "deadline_date", "distance", "map"]:
                # Partial match for text input filters
                filtered_df = filtered_df[filtered_df[column].astype(str).str.contains(value, case=False, na=False)]
    return filtered_df

def run_scraping(category, address, radius, keyword, custom_url, collection, progress_queue):
    """Run scraping in a background thread and send updates via queue."""
    lat, lon, city = get_coordinates(address)
    if not lat or not lon:
        logger.warning(f"Geocoding failed for address: {address}. Defaulting to Sydney NSW.")
        lat, lon, city = get_coordinates("Sydney NSW")
    
    results = []
    if category == "accommodation":
        scraper = scrape_accommodations(address, city, custom_url)
    else:
        scraper = scrape_jobs(address, radius, keyword, category, lat, lon, city, custom_url)

    try:
        for update in scraper:
            progress_queue.put(update)
            if "results" in update:
                results = update["results"]
    except Exception as e:
        logger.error(f"Scraping failed: {e}")
        progress_queue.put({"status": f"Error during scraping: {e}", "progress": 0, "error": True})
        return

    unique_results = {res['link']: res for res in results if 'link' in res}.values()

    if unique_results:
        for res in unique_results:
            res["category"] = category
            res["status"] = res.get("status", "new")
            res["distance"] = "N/A"  # Set default distance value
            if keyword:
                res["keyword"] = keyword
        progress_queue.put({"status": "Results processed", "progress": 1.0, "results": list(unique_results)})
    else:
        logger.warning("No results found during scraping.")
        progress_queue.put({"status": "No results found", "progress": 1.0, "results": []})

    progress_queue.put({"status": "Completed", "progress": 1.0})

def start_scraping(category, address, radius, keyword, custom_url, collection):
    """Start scraping in a background thread."""
    if st.session_state.scraping_thread and st.session_state.scraping_thread.is_alive():
        st.session_state.scraping_error = "Another search is already in progress"
        return
    progress_queue = queue.Queue()
    st.session_state.scraping_complete = False
    st.session_state.scraping_results = []
    st.session_state.scraping_status = "Starting search..."
    st.session_state.scraping_progress = 0
    st.session_state.scraping_error = None
    st.session_state.scraping_thread = threading.Thread(
        target=run_scraping,
        args=(category, address, radius, keyword, custom_url, collection, progress_queue)
    )
    st.session_state.scraping_thread.start()
    return progress_queue

def update_ui(progress_queue):
    """Update the UI with the latest scraping status from the queue."""
    progress_bar = st.empty()
    status_text = st.empty()
    while st.session_state.scraping_thread and st.session_state.scraping_thread.is_alive():
        try:
            update = progress_queue.get_nowait()
            st.session_state.scraping_progress = update.get("progress", 0)
            st.session_state.scraping_status = update.get("status", "")
            if update.get("error"):
                st.session_state.scraping_error = update["status"]
            if "results" in update:
                st.session_state.scraping_results = update["results"]
            progress_bar.progress(st.session_state.scraping_progress)
            status_text.text(st.session_state.scraping_status)
            if st.session_state.scraping_error:
                status_text.error(st.session_state.scraping_error)
        except queue.Empty:
            progress_bar.progress(st.session_state.scraping_progress)
            status_text.text(st.session_state.scraping_status)
            if st.session_state.scraping_error:
                status_text.error(st.session_state.scraping_error)
            time.sleep(0.1)  # Wait briefly before checking again
    # Check for final updates after thread completes
    while not progress_queue.empty():
        update = progress_queue.get()
        st.session_state.scraping_progress = update.get("progress", 0)
        st.session_state.scraping_status = update.get("status", "")
        if update.get("error"):
            st.session_state.scraping_error = update["status"]
        if "results" in update:
            st.session_state.scraping_results = update["results"]
        progress_bar.progress(st.session_state.scraping_progress)
        status_text.text(st.session_state.scraping_status)
        if st.session_state.scraping_error:
            status_text.error(st.session_state.scraping_error)
    st.session_state.scraping_complete = True

with tabs[0]:
    address = st.text_input("Enter your address (e.g., 123 Pitt St, Sydney NSW)")
    st.session_state.start_address = st.text_input("Enter start address for map directions (e.g., 456 King St, Melbourne VIC)")
    radius = st.slider("Radius (km)", 5, 50, 10)
    category_select = st.selectbox("Category", tab_names[1:])
    keyword = st.text_input("Additional keyword (optional)")
    custom_url = st.text_input("Optional custom link")

    if st.button("Search with Locator"):
        category = categories[tab_names.index(category_select) - 1]
        collection = "accommodations" if category == "accommodation" else "jobs"
        progress_queue = start_scraping(category, address, radius, keyword, custom_url, collection)

        # Update UI with scraping progress
        if progress_queue:
            update_ui(progress_queue)

    # Display results if complete
    if st.session_state.scraping_complete and st.session_state.scraping_results:
        results = st.session_state.scraping_results
        df = pd.DataFrame(results)
        columns = ["title", "company" if collection == "jobs" else "price", "location",
                   "keyword", "source", "posted_date", "deadline_date", "status", "distance", "link"]
        available_columns = [col for col in columns if col in df.columns]
        df = df[available_columns]

        # Add Map column with Google Maps URL using start_address and appending ", Adelaide SA" to destination
        start_address = st.session_state.start_address or "N/A"
        df['map'] = df['location'].apply(
            lambda x: f"https://www.google.com/maps/dir/?api=1&origin={urllib.parse.quote(start_address)}&destination={urllib.parse.quote(str(x) + ', Adelaide SA' if isinstance(x, str) else 'N/A, Adelaide SA')}"
        )
        available_columns.append('map')

        # Add filters
        st.subheader("Filter Results")
        filters = {}
        cols = st.columns(len(available_columns))
        for idx, col in enumerate(available_columns):
            with cols[idx]:
                if col in ["keyword", "location", "source", "status"]:
                    # Dropdown filter with unique values
                    unique_values = [""] + sorted(df[col].dropna().astype(str).unique().tolist())  # Include empty option
                    filters[col] = st.selectbox(
                        f"Filter {col.replace('_', ' ').title()}",
                        options=unique_values,
                        key=f"filter_{col}_search"
                    )
                else:
                    # Text input for other columns
                    filters[col] = st.text_input(
                        f"Filter {col.replace('_', ' ').title()}",
                        key=f"filter_{col}_search"
                    )

        # Apply filters
        filtered_df = apply_filters(df, filters)

        # Display total row count
        st.write(f"**Total Results: {len(filtered_df)}**")

        # Display editable table
        st.subheader("Search Results")
        try:
            column_config = {
                "link": st.column_config.LinkColumn("Link", display_text="Open"),
                "title": st.column_config.TextColumn("Title", width="large"),
                "company": st.column_config.TextColumn("Company", width="medium"),
                "price": st.column_config.TextColumn("Price", width="medium"),
                "location": st.column_config.TextColumn("Location", width="medium"),
                "keyword": st.column_config.TextColumn("Keyword", width="medium"),
                "source": st.column_config.TextColumn("Source", width="medium"),
                "posted_date": st.column_config.TextColumn("Posted Date", width="medium"),
                "deadline_date": st.column_config.TextColumn("Deadline Date", width="medium"),
                "status": st.column_config.TextColumn("Status", width="medium"),
                "distance": st.column_config.TextColumn("Distance", width="medium"),
                "map": st.column_config.LinkColumn("Map", display_text="View Map", width="small")
            }
            
            edited_df = st.data_editor(
                filtered_df,
                width="stretch",
                column_config={k: v for k, v in column_config.items() if k in available_columns},
                num_rows="dynamic",
                key=f"editor_{category}_search",
                disabled=["map"]  # Prevent editing of map column
            )

            # Save edited rows to database
            if st.button("Save Changes", key=f"save_{category}_search"):
                try:
                    for idx, row in edited_df.iterrows():
                        row_data = row.to_dict()
                        if "link" not in row_data or not row_data.get("link"):
                            new_link = str(uuid.uuid4())
                            edited_df.at[idx, "link"] = new_link
                            row_data["link"] = new_link
                            row_data["category"] = category
                            row_data["status"] = row_data.get("status", "new")
                            row_data["distance"] = row_data.get("distance", "N/A")
                            row_data["title"] = row_data.get("title", "N/A")
                            row_data["location"] = row_data.get("location", "N/A")
                            row_data["source"] = row_data.get("source", "N/A")
                            row_data["posted_date"] = row_data.get("posted_date", None)
                            row_data["deadline_date"] = row_data.get("deadline_date", None)
                            row_data["keyword"] = row_data.get("keyword", keyword or "N/A")
                            if collection == "jobs":
                                row_data["company"] = row_data.get("company", "N/A")
                            else:
                                row_data["price"] = row_data.get("price", "N/A")
                        update_listing(collection, row_data["link"], row_data)
                    st.success("Changes saved to database!")
                except Exception as e:
                    logger.error(f"Error saving changes to database: {e}")
                    st.error(f"Error saving changes: {e}")
        except Exception as e:
            logger.error(f"Error displaying data editor: {e}")
            st.error(f"Error displaying results: {e}")
    elif st.session_state.scraping_complete:
        st.error("No results found")

# Category tabs showing DB data
for i in range(1, 5):
    with tabs[i]:
        category = categories[i-1]
        collection = "accommodations" if category == "accommodation" else "jobs"

        # Add Refresh button
        if st.button("Refresh", key=f"refresh_{category}"):
            st.session_state[f"refresh_trigger_{category}"] = True

        # Fetch listings from database
        try:
            listings = get_listings(collection, {"category": category})
        except Exception as e:
            logger.error(f"Failed to fetch listings from database: {e}")
            st.error(f"Error fetching data: {e}")
            listings = []
        
        if listings:
            df = pd.DataFrame(listings)
            columns = ["title", "company" if collection == "jobs" else "price", "location",
                       "keyword", "source", "posted_date", "deadline_date", "status", "distance", "link"]
            available_columns = [col for col in columns if col in df.columns]
            df = df[available_columns]

            # Ensure distance column exists
            if 'distance' not in df.columns:
                df['distance'] = "N/A"

            # Add Map column with Google Maps URL using start_address and appending ", Adelaide SA" to destination
            start_address = st.session_state.start_address or "N/A"
            df['map'] = df['location'].apply(
                lambda x: f"https://www.google.com/maps/dir/?api=1&origin={urllib.parse.quote(start_address)}&destination={urllib.parse.quote(str(x) + ', Adelaide SA' if isinstance(x, str) else 'N/A, Adelaide SA')}"
            )
            available_columns.append('map')

            # Add filters
            st.subheader(f"Filter {tab_names[i]}")
            filters = {}
            cols = st.columns(len(available_columns))
            for idx, col in enumerate(available_columns):
                with cols[idx]:
                    if col in ["keyword", "location", "source", "status"]:
                        # Dropdown filter with unique values
                        unique_values = [""] + sorted(df[col].dropna().astype(str).unique().tolist())  # Include empty option
                        filters[col] = st.selectbox(
                            f"Filter {col.replace('_', ' ').title()}",
                            options=unique_values,
                            key=f"filter_{col}_{category}"
                        )
                    else:
                        # Text input for other columns
                        filters[col] = st.text_input(
                            f"Filter {col.replace('_', ' ').title()}",
                            key=f"filter_{col}_{category}"
                        )

            # Apply filters
            filtered_df = apply_filters(df, filters)

            # Display total row count
            st.write(f"**Total {tab_names[i]}: {len(filtered_df)}**")

            # Display editable table
            st.subheader(f"{tab_names[i]} Results")
            try:
                column_config = {
                    "link": st.column_config.LinkColumn("Link", display_text="Open"),
                    "title": st.column_config.TextColumn("Title", width="large"),
                    "company": st.column_config.TextColumn("Company", width="medium"),
                    "price": st.column_config.TextColumn("Price", width="medium"),
                    "location": st.column_config.TextColumn("Location", width="medium"),
                    "keyword": st.column_config.TextColumn("Keyword", width="medium"),
                    "source": st.column_config.TextColumn("Source", width="medium"),
                    "posted_date": st.column_config.TextColumn("Posted Date", width="medium"),
                    "deadline_date": st.column_config.TextColumn("Deadline Date", width="medium"),
                    "status": st.column_config.TextColumn("Status", width="medium"),
                    "distance": st.column_config.TextColumn("Distance", width="medium"),
                    "map": st.column_config.LinkColumn("Map", display_text="View Map", width="small")
                }
                
                edited_df = st.data_editor(
                    filtered_df,
                    width="stretch",
                    column_config={k: v for k, v in column_config.items() if k in available_columns},
                    num_rows="dynamic",
                    key=f"editor_{category}_db",
                    disabled=["map"]  # Prevent editing of map column
                )

                # Save edited rows to database
                if st.button("Save Changes", key=f"save_{category}_db"):
                    try:
                        updated_df = edited_df.copy()
                        for idx, row in updated_df.iterrows():
                            row_data = row.to_dict()
                            if "link" not in row_data or not row_data.get("link"):
                                new_link = str(uuid.uuid4())
                                updated_df.at[idx, "link"] = new_link
                                row_data["link"] = new_link
                                row_data["category"] = category
                                row_data["status"] = row_data.get("status", "new")
                                row_data["distance"] = row_data.get("distance", "N/A")
                                row_data["title"] = row_data.get("title", "N/A")
                                row_data["location"] = row_data.get("location", "N/A")
                                row_data["source"] = row_data.get("source", "N/A")
                                row_data["posted_date"] = row_data.get("posted_date", None)
                                row_data["deadline_date"] = row_data.get("deadline_date", None)
                                row_data["keyword"] = row_data.get("keyword", "N/A")
                                if collection == "jobs":
                                    row_data["company"] = row_data.get("company", "N/A")
                                else:
                                    row_data["price"] = row_data.get("price", "N/A")
                            original_row = df[df["link"] == row_data["link"]].iloc[0] if not df[df["link"] == row_data["link"]].empty else None
                            if original_row is not None and not pd.Series(row_data).equals(original_row):
                                update_listing(collection, row_data["link"], row_data)
                                logger.info(f"Updated row with link: {row_data['link']}")
                            elif original_row is None:
                                try:
                                    update_listing(collection, row_data["link"], row_data)
                                    logger.info(f"Inserted new row with link: {row_data['link']}")
                                except Exception as e:
                                    logger.error(f"Failed to insert new row with link {row_data['link']}: {e}")
                                    st.error(f"Failed to insert new row: {e}")
                        
                        original_links = set(df["link"])
                        edited_links = set(updated_df["link"])
                        deleted_links = original_links - edited_links
                        for deleted_link in deleted_links:
                            db = get_db()
                            db_collection = db[collection]
                            db_collection.delete_one({"link": deleted_link})
                            logger.info(f"Deleted row with link: {deleted_link}")
                        
                        st.success("Changes saved to database!")
                    except Exception as e:
                        logger.error(f"Error saving changes to database: {e}")
                        st.error(f"Error saving changes: {e}")
            except Exception as e:
                logger.error(f"Error displaying data editor for category {category}: {e}")
                st.error(f"Error displaying results: {e}")
        else:
            st.info("No data in this category yet.")