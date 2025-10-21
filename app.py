import streamlit as st
import pandas as pd
from geocode import get_coordinates
from scrapers import scrape_jobs, scrape_accommodations
from database import save_listings, get_listings, update_listing, get_db
import uuid
import logging

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

tabs = st.tabs(tab_names)

def apply_filters(df, filters):
    """Apply filters to the dataframe based on user input."""
    filtered_df = df.copy()
    for column, value in filters.items():
        if value:
            if column in ["title", "location", "source", "company", "price", "keyword"]:
                filtered_df = filtered_df[filtered_df[column].str.contains(value, case=False, na=False)]
            elif column in ["posted_date", "deadline_date", "status"]:
                filtered_df = filtered_df[filtered_df[column].astype(str).str.contains(value, case=False, na=False)]
    return filtered_df

def run_scraping(category, address, radius, keyword, custom_url, collection):
    """Run scraping and update progress in the main thread."""
    lat, lon, city = get_coordinates(address)
    if not lat or not lon:
        logger.warning(f"Geocoding failed for address: {address}. Defaulting to Sydney NSW.")
        lat, lon, city = get_coordinates("Sydney NSW")
    
    results = []
    progress_bar = st.progress(0)
    status_text = st.empty()

    if category == "accommodation":
        scraper = scrape_accommodations(address, radius, lat, lon, city, custom_url)
    else:
        scraper = scrape_jobs(address, radius, keyword, category, lat, lon, city, custom_url)

    try:
        for update in scraper:
            progress_bar.progress(update["progress"])
            status_text.write(update["status"])
            if "results" in update:
                results = update["results"]
    except Exception as e:
        logger.error(f"Scraping failed: {e}")
        status_text.error(f"Error during scraping: {e}")
        return

    unique_results = {res['link']: res for res in results if 'link' in res}.values()

    if unique_results:
        for res in unique_results:
            res["category"] = category
            res["status"] = res.get("status", "new")
            # Ensure keyword is saved
            if keyword:
                res["keyword"] = keyword
        try:
            save_listings(collection, list(unique_results))
            st.session_state.scraping_results = list(unique_results)
        except Exception as e:
            logger.error(f"Failed to save listings to database: {e}")
            status_text.error(f"Failed to save results to database: {e}")
    else:
        logger.warning("No results found during scraping.")
        st.session_state.scraping_results = []

    st.session_state.scraping_complete = True

with tabs[0]:
    address = st.text_input("Enter your address (e.g., 123 Pitt St, Sydney NSW)")
    radius = st.slider("Radius (km)", 5, 50, 10)
    category_select = st.selectbox("Category", tab_names[1:])
    keyword = st.text_input("Additional keyword (optional)")
    custom_url = st.text_input("Optional custom link")

    if st.button("Search with Locator"):
        category = categories[tab_names.index(category_select) - 1]
        collection = "accommodations" if category == "accommodation" else "jobs"
        st.session_state.scraping_progress = 0
        st.session_state.scraping_status = "Starting search..."
        st.session_state.scraping_complete = False
        st.session_state.scraping_results = []

        # Run scraping in the main thread
        run_scraping(category, address, radius, keyword, custom_url, collection)

    # Display results if complete
    if 'scraping_complete' in st.session_state and st.session_state.scraping_complete:
        results = st.session_state.scraping_results
        if results:
            df = pd.DataFrame(results)
            # Updated columns to include keyword
            columns = ["title", "company" if collection == "jobs" else "price", "location", 
                      "keyword", "source", "posted_date", "deadline_date", "status", "link"]
            available_columns = [col for col in columns if col in df.columns]
            df = df[available_columns]

            # Add filters
            st.subheader("Filter Results")
            filters = {}
            cols = st.columns(len(available_columns))
            for idx, col in enumerate(available_columns):
                with cols[idx]:
                    filters[col] = st.text_input(f"Filter {col.replace('_', ' ').title()}", key=f"filter_{col}")

            # Apply filters
            filtered_df = apply_filters(df, filters)

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
                }
                
                edited_df = st.data_editor(
                    filtered_df,
                    width="stretch",
                    column_config={k: v for k, v in column_config.items() if k in available_columns},
                    num_rows="dynamic",
                    key=f"editor_{category}"
                )

                # Save edited rows to database
                if st.button("Save Changes", key=f"save_{category}"):
                    try:
                        # Create a copy of edited_df to modify
                        updated_df = edited_df.copy()
                        
                        for idx, row in updated_df.iterrows():
                            row_data = row.to_dict()
                            
                            # Handle new rows
                            if "link" not in row_data or not row_data.get("link"):
                                # Generate unique link for new row
                                new_link = str(uuid.uuid4())
                                updated_df.at[idx, "link"] = new_link
                                row_data["link"] = new_link
                                # Set default values for required fields
                                row_data["category"] = category
                                row_data["status"] = row_data.get("status", "new")
                                row_data["title"] = row_data.get("title", "")
                                row_data["location"] = row_data.get("location", "")
                                row_data["source"] = row_data.get("source", "")
                                row_data["posted_date"] = row_data.get("posted_date", "")
                                row_data["deadline_date"] = row_data.get("deadline_date", "")
                                row_data["keyword"] = row_data.get("keyword", "")
                                if collection == "jobs":
                                    row_data["company"] = row_data.get("company", "")
                                else:
                                    row_data["price"] = row_data.get("price", "")
                            
                            # Check if row exists in original DataFrame
                            original_row = df[df["link"] == row_data["link"]].iloc[0] if not df[df["link"] == row_data["link"]].empty else None
                            if original_row is not None and not pd.Series(row_data).equals(original_row):
                                # Update existing row
                                update_listing(collection, row_data["link"], row_data)
                                logger.info(f"Updated row with link: {row_data['link']}")
                            elif original_row is None:
                                # Insert new row
                                try:
                                    update_listing(collection, row_data["link"], row_data)
                                    logger.info(f"Inserted new row with link: {row_data['link']}")
                                except Exception as e:
                                    logger.error(f"Failed to insert new row with link {row_data['link']}: {e}")
                                    st.error(f"Failed to insert new row: {e}")
                        
                        # Handle deleted rows
                        original_links = set(df["link"])
                        edited_links = set(updated_df["link"])
                        deleted_links = original_links - edited_links
                        for deleted_link in deleted_links:
                            db = get_db()
                            db_collection = db[collection]
                            db_collection.delete_one({"link": deleted_link})
                            logger.info(f"Deleted row with link: {deleted_link}")
                        
                        # Update session state to reflect changes
                        st.session_state.scraping_results = updated_df.to_dict("records")
                        st.success("Changes saved to database!")
                    except Exception as e:
                        logger.error(f"Error saving changes to database: {e}")
                        st.error(f"Error saving changes: {e}")
            except Exception as e:
                logger.error(f"Error displaying data editor: {e}")
                st.error(f"Error displaying results: {e}")
        else:
            st.error("No results found")

# Category tabs showing DB data
for i in range(1, 5):
    with tabs[i]:
        category = categories[i-1]
        collection = "accommodations" if category == "accommodation" else "jobs"
        try:
            listings = get_listings(collection, {"category": category})
        except Exception as e:
            logger.error(f"Failed to fetch listings from database: {e}")
            st.error(f"Error fetching data: {e}")
            listings = []
        
        if listings:
            df = pd.DataFrame(listings)
            # Updated columns to include keyword
            columns = ["title", "company" if collection == "jobs" else "price", "location", 
                      "keyword", "source", "posted_date", "deadline_date", "status", "link", "scraped_at"]
            available_columns = [col for col in columns if col in df.columns]
            df = df[available_columns]

            # Add filters
            st.subheader(f"Filter {tab_names[i]}")
            filters = {}
            cols = st.columns(len(available_columns))
            for idx, col in enumerate(available_columns):
                with cols[idx]:
                    filters[col] = st.text_input(f"Filter {col.replace('_', ' ').title()}", key=f"filter_{col}_{category}")

            # Apply filters
            filtered_df = apply_filters(df, filters)

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
                    "scraped_at": st.column_config.DatetimeColumn("Scraped At", width="medium"),
                }
                
                edited_df = st.data_editor(
                    filtered_df,
                    width="stretch",
                    column_config={k: v for k, v in column_config.items() if k in available_columns},
                    num_rows="dynamic",
                    key=f"editor_{category}_db"
                )

                # Save edited rows to database
                if st.button("Save Changes", key=f"save_{category}_db"):
                    try:
                        # Create a copy of edited_df to modify
                        updated_df = edited_df.copy()
                        
                        for idx, row in updated_df.iterrows():
                            row_data = row.to_dict()
                            
                            # Handle new rows
                            if "link" not in row_data or not row_data.get("link"):
                                # Generate unique link for new row
                                new_link = str(uuid.uuid4())
                                updated_df.at[idx, "link"] = new_link
                                row_data["link"] = new_link
                                # Set default values for required fields
                                row_data["category"] = category
                                row_data["status"] = row_data.get("status", "new")
                                row_data["title"] = row_data.get("title", "")
                                row_data["location"] = row_data.get("location", "")
                                row_data["source"] = row_data.get("source", "")
                                row_data["posted_date"] = row_data.get("posted_date", "")
                                row_data["deadline_date"] = row_data.get("deadline_date", "")
                                row_data["keyword"] = row_data.get("keyword", "")
                                if collection == "jobs":
                                    row_data["company"] = row_data.get("company", "")
                                else:
                                    row_data["price"] = row_data.get("price", "")
                            
                            # Check if row exists in original DataFrame
                            original_row = df[df["link"] == row_data["link"]].iloc[0] if not df[df["link"] == row_data["link"]].empty else None
                            if original_row is not None and not pd.Series(row_data).equals(original_row):
                                # Update existing row
                                update_listing(collection, row_data["link"], row_data)
                                logger.info(f"Updated row with link: {row_data['link']}")
                            elif original_row is None:
                                # Insert new row
                                try:
                                    update_listing(collection, row_data["link"], row_data)
                                    logger.info(f"Inserted new row with link: {row_data['link']}")
                                except Exception as e:
                                    logger.error(f"Failed to insert new row with link {row_data['link']}: {e}")
                                    st.error(f"Failed to insert new row: {e}")
                        
                        # Handle deleted rows
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