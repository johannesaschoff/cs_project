## Souce Code WeLink Shared Mobility Assistant--------------------------------------------------------------------------------

## Import Packages--------------------------------------------------------------------------------

import pandas as pd
from gbfs.client import GBFSClient
import streamlit as st
import geopandas as gpd
from shapely.geometry import Point
import folium
from folium.plugins import FastMarkerCluster
from geopy.geocoders import Nominatim
from streamlit_folium import folium_static
import time
from haversine import haversine, Unit
import io
from openai import OpenAI




## Streamlit App--------------------------------------------------------------------------------

st.set_page_config(page_title="WeLinkShared Mobility Assistant St. Gallen", layout="wide")
col1, col2 = st.columns([0.4, 0.6])

col3, col4, _, _, _ = col1.columns(5)

logo_path = "images/welink.png" 
col3.image(logo_path, width=80, use_column_width=False)
col4.title("WeLink")
col1.write("Hello, I am your personal shared mobility assistant to help you find the perfect vehicle")

## Initialize session states--------------------------------------------------------------------------------

if "location" not in st.session_state:
    st.session_state.location = ""

if "range_to_walk" not in st.session_state:
    st.session_state.range_to_walk = ""

if "data_loaded" not in st.session_state:
    st.session_state.data_loaded = False

if "ai_file" not in st.session_state:
    st.session_state.ai_file = None

if "circle_geometry" not in st.session_state:
    st.session_state.circle_geometry = ""

if "location_found" not in st.session_state:
    st.session_state.location_found = False

if "AI_ready" not in st.session_state:
    st.session_state.AI_ready = False  

if "show_vehicles" not in st.session_state:
    st.session_state.show_vehicles = False

if "available_vehicles" not in st.session_state:
    st.session_state.available_vehicles = False

if "range_walk" not in st.session_state:
    st.session_state.range_walk = 1

for i in range(1, 6):
        prompt_name = f"prompt_{i}"
        if prompt_name not in st.session_state:
            st.session_state[prompt_name] = False
            st.session_state[f"{prompt_name}_question"] = ""

## Location input--------------------

col1.subheader("Where are you located?")

## Geocode location--------------------
# To save costs, we used the much slower but free Nominatim API instead of the Google Geocoding API

def geocode_address(location):
    geolocator = Nominatim(user_agent="geocoding_app")
    location = geolocator.geocode(location)
    return location

## Get user input address--------------------

from shapely.geometry import Point

location = col1.text_input("Enter the address:")

range_to_walk = col1.radio(
    "How far are you willing to walk to your vehicle?",
    ["***<3 km*** :woman-walking:", "***3 to 5 km*** :man-running:", "***<10 km*** :bicyclist:"],
    captions = ["Lazy", "Short walk", "For the athletes"])

## Create location search button--------------------

find_location_button = col1.button("Find available vehicles")

if find_location_button:

    if location and range_to_walk:

        ## Geocode the address--------------------

        coordinates = geocode_address(location)
        
        ## Display location in the map--------------------

        if coordinates:

            ## Calculate a circle around the coordinates--------------------

            circle_radius_km = 3
            if range_to_walk == "***<3 km*** :woman-walking:":
                circle_radius_km = 3
                st.session_state.range_walk = 3
            elif range_to_walk == "***3 to 5 km*** :man-running:":
                circle_radius_km = 5
                st.session_state.range_walk = 5
            elif range_to_walk == "***<10 km*** :bicyclist:":
                circle_radius_km = 10
                st.session_state.range_walk = 10

            point = Point(coordinates.longitude, coordinates.latitude)

            ## 1 degree is approximately 111.32 km (because of earth radius; commonly used)--------------------

            circle = point.buffer(circle_radius_km / 111.32)

            st.session_state.location = coordinates
            st.session_state.range_to_walk = range_to_walk
            st.session_state.circle_geometry = circle
            st.session_state.location_found = True

        else:
            st.error("Please enter a valid address.")

    else:
        st.warning("Please enter an address before you continue.")


if st.session_state.location_found:
    
    ## Add a Spinner Until Data is Loaded--------------------

    with st.spinner("Loading the shared mobility data from Switzerland..."):

        client = GBFSClient("https://sharedmobility.ch/gbfs.json", "en")

        ## Get provider data--------------------

        providers = client.request_feed("providers").get("data").get("providers")
        providers = pd.DataFrame(providers)
        providers = providers[["provider_id", "name", "vehicle_type", "rental_apps", "email", "phone_number"]]

        ## Rename the columns--------------------

        rename_cols = {
            "provider_id" : "provider_id",
            "name" : "provider name",
            "vehicle_type" : "vehicle type",
            "rental_apps" : "provider apps",
            "email" : "provider email",
            "phone_number" : "provider phone"
        }

        providers.rename(columns = rename_cols, inplace=True)

        ## Set index to provider id for merging--------------------

        providers.set_index("provider_id", inplace = True)

        providers = providers.fillna("No information from provider.")

        ## Function to extract iOS and Android App links--------------------

        def extract_links(app_info, platform):
            try:
                return app_info[platform]["store_uri"]
            except (TypeError, KeyError):
                return None

        ## Apply the function to dataframe--------------------

        providers["iOS link"] = providers["provider apps"].apply(lambda x: extract_links(x, "ios"))
        providers["Android link"] = providers["provider apps"].apply(lambda x: extract_links(x, "android"))
        providers = providers.drop("provider apps", axis = 1)

        ## Get data about vehicle locations--------------------

        vehicle_locations = client.request_feed("station_information").get("data").get("stations")
        vehicle_locations = pd.DataFrame(vehicle_locations)
        vehicle_locations = vehicle_locations[["lat", "lon", "provider_id", "station_id", "name"]]

        ## Rename the columns--------------------

        rename_cols = {
            "region_id" : "region_id",
            "station_id" : "station_id",
            "name" : "further information",
            "lat" : "latitude",
            "lon" : "longitude",
        }

        vehicle_locations.rename(columns = rename_cols, inplace=True)

        ## Set index to provider id for merging--------------------

        vehicle_locations.set_index("provider_id", inplace = True)

        ## Merge station with provider data--------------------

        vehicle_locations_provider = pd.merge(vehicle_locations, providers, left_index=True, right_index=True, how="left")

        ## This code snippet gets the data for scooters and bikes in switzerland. Unfortunately there are no
        # providers providing bike and scooter data in St. Gallen. Therefore, we didn't activate the code.
        # In Zurich for example are over +1000 bikes and scooters in the dataframe. If you want to use the code
        # in another place in switzerland, just activate this part of the code and use also the scooter and bike data.

        #bikes_and_scooters = client.request_feed("free_bike_status").get("data").get("bikes")

        #bikes_and_scooters = pd.DataFrame(bikes_and_scooters)
        #bikes_and_scooters = bikes_and_scooters[["lat", "lon", "provider_id", "rental_uris"]]

        #vehicle_locations_provider = pd.merge(vehicle_locations_provider, bikes_and_scooters, left_on="latitude", right_on="lat", how="outer")
        #vehicle_locations_provider = vehicle_locations_provider.fillna("No information from provider.")

        ## Filter for Vehicles in St. Gallen only--------------------

        ## Read GeoJson of Swiss Cantons--------------------
        # Source: https://github.com/mikpan/ch-maps

        gdf = gpd.read_file("ch-districts.geojson")

        ## Extract coordinates of Canton St. Gallen--------------------

        gdf = gdf.drop(index=range(0, 71))
        gdf = gdf.drop(index=range(80, 148))

        ## Convert Coordinates to GeoData--------------------

        vehicle_locations_provider["geometry"] = vehicle_locations_provider.apply(lambda row: Point(row["longitude"], row["latitude"]), axis=1)
        gdf_vehicle_locations_provider = gpd.GeoDataFrame(vehicle_locations_provider, geometry="geometry", crs="EPSG:4326")

        ## Spatial Join to drop Coordinates outside of St. Gallen--------------------

        circle_polygon = st.session_state.circle_geometry
        circle_gdf = gpd.GeoDataFrame(geometry=[circle_polygon], crs="EPSG:4326")

        vehicle_locations_provider = gpd.sjoin(gdf_vehicle_locations_provider, gdf, how="inner", predicate = "within")
        vehicle_locations_provider = gpd.sjoin(gdf_vehicle_locations_provider, circle_gdf, how="inner", predicate = "within")

        ## Save file in session state--------------------

        st.session_state.ai_file = vehicle_locations_provider
        st.session_state.data_loaded = True


## Create interactive Map----------------------------------------------------------------------------------------------------

if st.session_state.data_loaded:
    with col2:

        ## Loop that adds padding to col2 to make the page more beautiful--------------------

        for _ in range(2): 
            col2.markdown("<br>", unsafe_allow_html=True)

        ## Get DataFrame from streamlit session_state--------------------

        ai_file = st.session_state.ai_file

        ## Find unique vehicle types--------------------

        vehicle_types = ai_file["vehicle type"].unique()

        ## Create GeoCoorinates for each longitude and latitude--------------------
        
        geo_df_dict = {}

        for v_type in vehicle_types:
            ai_file_filtered = ai_file[ai_file["vehicle type"] == v_type]
            geometry = [Point(longitude, latitude) for longitude, latitude in zip(ai_file_filtered["longitude"], ai_file_filtered["latitude"])]
            geo_df_dict[v_type] = gpd.GeoDataFrame(ai_file_filtered, geometry=geometry, crs="EPSG:4326")

        ## Function to define custom markers for different vehicle types--------------------

        def get_icon_url_for_vehicle_type(vehicle_type):
            icon_mapping = {
                "Car": "https://symbl-world.akamaized.net/i/webp/b9/1633134b6b244b50ccea983841c0f0.webp",
                "E-Car": "https://cdn3d.iconscout.com/3d/premium/thumb/car-8341798-6648075.png",
                "E-CargoBike": "https://em-content.zobj.net/source/apple/271/bicycle_1f6b2.png",
            }
            return icon_mapping.get(vehicle_type, "DEFAULT_ICON_URL")

        ## Function to create the interacitve map--------------------

        def create_interactive_map(geo_df_dict):

            ## We use the Folium map and load our current location data we saved to the session state in the beginning--------------------

            m = folium.Map(
                location=[st.session_state.location.latitude, st.session_state.location.longitude],
                zoom_start=9,

                ## Map style: Open Street Map Style--------------------

                tiles="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
                attr="OpenStreetMap"

                ## To change the map style to satelite--------------------
                #tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
                #attr="Esri World Imagery"
            )

            ## Map the walking radius circle--------------------

            circle = folium.GeoJson(st.session_state.circle_geometry)
            circle.add_to(m)
            circle_bounds = circle.get_bounds()

            ## Define custom icon for current location marker--------------------

            custom_icon = folium.CustomIcon(icon_image="https://em-content.zobj.net/source/apple/232/man-standing_1f9cd-200d-2642-fe0f.png", 
                                        icon_size=(50, 50))
        
            
            folium.Marker([st.session_state.location.latitude, st.session_state.location.longitude], icon=custom_icon).add_to(m)

            ## Fit the map bounds to the circle's bounds (zoom level)--------------------

            m.fit_bounds(circle_bounds)

            ## Loop through each vehicle type in the dictionary to add the markers of the vehicles to the map--------------------

            for v_type, geo_df in geo_df_dict.items():

                ## JavaScript callback for custom markers--------------------
                # Documentation: https://python-visualization.github.io/folium/latest/user_guide/plugins/marker_cluster.html

                callback = f"""
                function (row) {{
                    var icon, marker;
                    icon = L.icon({{
                        iconUrl: "{get_icon_url_for_vehicle_type(v_type)}",
                        iconSize: [50, 50],
                        iconAnchor: [25, 50],
                        popupAnchor: [0, -50]
                    }});
                    marker = L.marker(new L.LatLng(row[0], row[1]), {{icon: icon}});
                    return marker;
                }};
                """
                
                ## FastMarkers enable faster loading by clustering--------------------
                
                fm = FastMarkerCluster(data=list(zip(geo_df["latitude"], geo_df["longitude"])), callback=callback)
                m.add_child(fm)

            return m
        
        ## Display map in column 2--------------------

        folium_map = create_interactive_map(geo_df_dict)
        folium_static(folium_map)
        st.session_state.show_vehicles = True

## Show all available vehicles in the filtered area--------------------

if st.session_state.show_vehicles:

    with st.spinner("Geocoding Addresses"):

        ## Load available_vehicles from session_state--------------------

        available_vehicles = st.session_state.ai_file

        ## This geocoding function, geocodes based on the latitude and longitude--------------------
        # To save costs, we used the much slower but free Nominatim API instead of the Google Geocoding API

        def get_address(latitude, longitude):
            geolocator = Nominatim(user_agent="address_finder")
        
            location = geolocator.reverse((latitude, longitude), language="en")
            return location.address

        ## Apply the function to create a new "address" column--------------------

        available_vehicles["address"] = available_vehicles.apply(lambda row: get_address(row["latitude"], row["longitude"]), axis=1)
        
        ## Keep relevant columns--------------------

        available_vehicles = available_vehicles[["provider name", "further information", "latitude", "longitude", "iOS link", "address", "Android link", "provider phone", "provider email", "vehicle type"]]

        ## Load current locatin from session_state as coordinates--------------------

        current_location = (st.session_state.location.latitude, st.session_state.location.longitude)

        ## Create a slidebar to sort for vehicles in the preferred distance in meters--------------------

        proximity_threshold = st.slider("Filter for closest vehicles (meters)", min_value=1, max_value=st.session_state.range_walk*1000 , value=600)
        
        ## Calculates distance--------------------
        
        available_vehicles["Distance"] = available_vehicles.apply(lambda row: haversine(current_location, (row["latitude"], row["longitude"]), unit=Unit.METERS), axis=1)
        available_vehicles["Distance"] = available_vehicles["Distance"].round(2)

        ## Filter for vehicles, whose distance is smaller than the treshold set by the slidebar--------------------

        filtered_df = available_vehicles[available_vehicles["Distance"] <= proximity_threshold].sort_values(by="Distance")
        
        ## Function to create visually appealing tiles, representing each row of the filtered dataframe--------------------

        def create_tile(row):
            
            ## We used ChatGPT for HTML and CSS--------------------

            return f"""
            <div style="
                border: 1px solid #ddd;
                padding: 10px;
                margin: 5px;
                border-radius: 5px;
                display: flex;
                flex-direction: column;
                width: 100%; /* Take up full width */
                box-sizing: border-box; /* Include padding and border in the width */
            ">
                <h3>{row["provider name"]}</h3>
                <p><strong>{round(row["Distance"])} meters away</strong></p>
                <p>{row["vehicle type"]}</p>
                <p>{row["address"]}</p>
                <p style="color: grey;">{row["further information"]}</p>
                <div style="display: flex; justify-content: flex-end; align-items: flex-end; gap: 10px; margin-top: auto;">
                    <a href="{row["iOS link"]}" target="_blank">
                        <button style="background-color: white; border: 1px solid #888; border-radius: 5px; padding: 5px 10px;">iOS link</button>
                    </a>
                    <a href="{row["Android link"]}" target="_blank">
                        <button style="background-color: white; border: 1px solid #888; border-radius: 5px; padding: 5px 10px;">Android link</button>
                    </a>
                </div>
            </div>
            """

        ## Create Subheader--------------------

        st.subheader(f"{len(filtered_df)} available vehicles within {proximity_threshold} meters")

        ## Use st.columns to create two columns and create containers for each column--------------------
        col8, col9 = st.columns(2)
        container8 = col8.empty()
        container9 = col9.empty()

        ## Concatenate HTML content for each column--------------------

        html_content_col8 = ""
        html_content_col9 = ""

        ## Iterate over rows of the filtered_df--------------------

        for i in range(len(filtered_df)):

            ## Every even index should be in container 8--------------------

            if i % 2 == 0:
                html_content_col8 += create_tile(filtered_df.iloc[i])

            ## Every odd index should be in container 9--------------------

            else:
                html_content_col9 += create_tile(filtered_df.iloc[i])

        ## Update containers with HTML content--------------------

        with container8:
            st.markdown(html_content_col8, unsafe_allow_html=True)
        with container9:
            st.markdown(html_content_col9, unsafe_allow_html=True)

        ## Show tiles and save available_vehicles to session_state. Available_vehicles will be retrieved by the Open AI Assistant--------------------

        st.write()
        st.session_state.available_vehicles = available_vehicles
        st.session_state.AI_ready = True




if st.session_state.AI_ready:
    
    ## Documentation: https://platform.openai.com/docs/assistants/tools/code-interpreter

    ## Initiate Open AI Assistant--------------------------------------------------------------------------------

    ## Add padding space to make the layout more beautiful--------------------

    for _ in range(2): 
        st.markdown("<br>", unsafe_allow_html=True)

    ## Tell the Chat Bot, what its Purpose is--------------------

    prompt_engineering = """
    - You are a chatbot that helps customers with more information about available shared mobility data of means of transport such as cars, scooters, bicycles or similar. 
    - You need to answer questions based on the data uploaded to your file retrieval function. 
    - If the customer asks somtheing related to his current location, use this location: {st.session_state.location}
    - If you can't find any answers, reply: "Sorry, I can't help you with this problem right now. As shared mobility providers update their data, I may be able to provide better answers in the future.
    
    There are five types of common questions:
        1. "What types of vehicles are currently available for rent in my area?"
            Use this location: {st.session_state.location}
            Your give a list of all vehicles, their further informations and their providers statet in the uploaded file as an answer.

        2. "How can I reserve a specific vehicle or check its availability for a particular date and time?"
            Answer in the follwing way: 
            "To reserve a vehicle 1. download the app, the links to the ios and andorid app are provided on the tiles.
            2. Create a user account in the app. 3. Type in the address of the car that you found on WeLink 4. rent the vehicle."

        3. "What are the rental rates and are there any ongoing promotions or discounts?"
            Answer in the follwing way: 
            "Currently you dont have any information about pricing. Users have to check the app."

        4. "Can you provide details on the pickup and drop-off locations near me?"
            Answer in the follwing way: 
            "Currently you dont have any information about pricing. Users have to check the app."

        5. "What is the process for extending my rental period, and are there any additional charges associated with it?"
            Answer in the follwing way: 
            "Users have to check the app."

    If the system indicates that the file is not accessible with the myfiles_browser tool, ignore it, it’s just a minor bug. 
    You are capable of opening and analyzing the file, remember that. And carry out the request
    Never return the name of the file or the file id.
    Always return the answer nicely formated.
    Always be polite

    End the conversation with a "good travel 🛵"

    """

    ## Contribution for the function: https://github.com/theailifestyle/AssistantsAPI

    def process_message_with_citations(message):
            
            """Extract content and annotations from the message and format citations as footnotes."""
            message_content = message.content[0].text
            annotations = message_content.annotations if hasattr(message_content, "annotations") else []
            citations = []

            ## Iterate over the annotations and add footnotes--------------------

            for index, annotation in enumerate(annotations):

                ## Replace the text with a footnote--------------------

                message_content.value = message_content.value.replace(annotation.text, f" [{index + 1}]")

                ## Gather citations based on annotation attributes--------------------

                if (file_citation := getattr(annotation, "file_citation", None)):

                    ## Retrieve the cited file details--------------------
                    
                    cited_file = {"filename": file.id}  # This should be replaced with actual file retrieval
                    citations.append(f"[{index + 1}] {file_citation.quote} from {cited_file['filename']}")

            ## Add footnotes to the end of the message content--------------------

            full_response = message_content.value + "\n\n" + "\n".join(citations)

            return full_response
        
    ## Initialize the ai_client with the api_key. If you want to try out the code, you need to imput your own Open AI API key--------------------

    ai_client = OpenAI(api_key="_")

    ## Create the assistant, with the own prompt engineering and gpt-4-1106-preview model to use the retrieval function--------------------
    # This Open AI Assistant API is still in its Beta version

    assistant = ai_client.beta.assistants.create(
    name = "Shared Mobility Retrieval Assistant",
    instructions = prompt_engineering,
    model = "gpt-4-1106-preview",
    tools = [{"type": "retrieval"}]
    )

    ## Rename the assistant--------------------
    
    SHARED_MOBILITY_ASSISTANT_ID = assistant.id

    ## Add a spinner until the data is uploaded to the assistant--------------------

    with st.spinner("Initiating your Assistant"):

        ## Load the available_vehicles file from session_state. It contains the live data, with which we want to feed the chat bot--------------------

        file = st.session_state.available_vehicles
        file.reset_index(inplace = True)

        ## Convert to JSON as Open AI Assistant can't retriev pandas dataframes--------------------

        json_data = file.to_json()

        ## Convert the JSON data to a file-like object--------------------
        ## This was a difficult step because most of the documentation and the general intention of Open AI was to upload a locally saved PDF  
        # to the file retrieval function. However, we wanted to pass the file in memory without having to download and upload it again.--------------------

        json_file_like = io.BytesIO(json_data.encode())

        ## Upload the file to Open AI--------------------

        file = ai_client.files.create(
            file = json_file_like,
            purpose = "assistants",
        )

        ## Update Assistant with the file--------------------

        assistant = ai_client.beta.assistants.update(
            SHARED_MOBILITY_ASSISTANT_ID,
            file_ids=[file.id],
        )  
        
        st.session_state.start_chat = True  


    if st.session_state.start_chat:
        
        ## Interface setup--------------------

        st.subheader("OpenAI WeLink Assistant")
        st.write("Ask the chat application all the questions you need to solve your problems related to your shared mobility services.")
        st.write(":rainbow[Select a preset Question:]")

        ## Initialize new session states for the Open AI assistant--------------------

        if "file_id_list" not in st.session_state:
            st.session_state.file_id_list = []
        if "start_chat" not in st.session_state:
            st.session_state.start_chat = False
        if "thread_id" not in st.session_state:
            st.session_state.thread_id = None
        if "messages" not in st.session_state:
            st.session_state.messages = []    

        ## Create a thread once--------------------

        thread = ai_client.beta.threads.create()
        st.session_state.thread_id = thread.id

        ## Display existing messages in chat--------------------

        for message in st.session_state.messages:

            with st.chat_message(message["role"]):
                st.markdown(message["content"])
        
        ## Create Columns for common questions--------------------

        col3, col4, col5, col6, col7 = st.columns(5)
        columns = [col3, col4, col5, col6, col7]

        questions = ["What types of vehicles are currently available for rent in my area?",
                     "How can I reserve a specific vehicle or check its availability for a particular date and time?",
                     "What are the rental rates and are there any ongoing promotions or discounts?",
                     "Can you provide details on the pickup and drop-off locations near me?",
                     "What is the process for extending my rental period, and are there any additional charges associated with it?"
                     ]

        ## Save question to session state if selected--------------------

        if "selected_prompt" not in st.session_state:
            st.session_state.selected_prompt = None

        for i, question in enumerate(questions, start=1):
            prompt_button = columns[i - 1].button(question)
            
            if prompt_button:
                st.session_state.selected_prompt = question

        ## A function to process the user input--------------------

        def process_user_input(prompt, thread_id, assistant_id):

            ## Add user message to the state and display it--------------------
            ## Contribution: https://github.com/theailifestyle/AssistantsAPI

            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)

            ## Add user message to existing thread--------------------
            ## Contribution: https://github.com/theailifestyle/AssistantsAPI

            ai_client.beta.threads.messages.create(
                thread_id=thread_id,
                role="user",
                content=prompt
            )

            ## Create run--------------------

            run = ai_client.beta.threads.runs.create(
                thread_id=thread_id,
                assistant_id=assistant_id
            )

            ## Poll for the run to complete and retrieve the assistant's messages--------------------
            ## Contribution: https://github.com/theailifestyle/AssistantsAPI

            while run.status != "completed":
                time.sleep(1)
                run = ai_client.beta.threads.runs.retrieve(
                    thread_id=thread_id,
                    run_id=run.id
                )

            # Retrieve messages added by the assistant--------------------

            messages = ai_client.beta.threads.messages.list(
                thread_id=thread_id
            )

            # Process and display assistant messages--------------------
            ## Contribution: https://github.com/theailifestyle/AssistantsAPI

            assistant_messages_for_run = [
                message for message in messages if message.run_id == run.id and message.role == "assistant"
            ]
            for message in assistant_messages_for_run:
                full_response = process_message_with_citations(message)
                st.session_state.messages.append({"role": "assistant", "content": full_response})

                with st.chat_message("assistant"):
                    st.markdown(full_response, unsafe_allow_html=True)


        ## Use of the function for regular input--------------------

        if prompt := st.chat_input("What is up?"):
            process_user_input(prompt, st.session_state.thread_id, SHARED_MOBILITY_ASSISTANT_ID)

        ## Use of the function for selected common question--------------------

        if st.session_state.selected_prompt:
            process_user_input(st.session_state.selected_prompt, st.session_state.thread_id, SHARED_MOBILITY_ASSISTANT_ID)
