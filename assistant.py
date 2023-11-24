import gbfs
import pandas as pd
from gbfs.services import SystemDiscoveryService
from gbfs.client import GBFSClient
import streamlit as st
import numpy as np
import streamlit as st
import geopandas as gpd
from shapely.geometry import Point
import folium
from folium.plugins import FastMarkerCluster
from streamlit_folium import folium_static
import sys
import time

# Streamlit App------------------------------
st.set_page_config(page_title="Shared Mobility Assistant", page_icon=":speech_balloon:")

st.title("Shared Mobility Assistant")
st.write("Hello, I am your personal assistant to help you find the perfect vehicle")

# Add a spinner until the data is loaded
with st.spinner("Loading the shared mobility data from switzerland..."):
    
    client = GBFSClient('https://sharedmobility.ch/gbfs.json', 'en')

    # Display System Information--------------------

    system_information = client.request_feed('system_information')
    system_information = pd.DataFrame(system_information)

    ## get providers

    providers = client.request_feed('providers').get('data').get('providers')
    providers = pd.DataFrame(providers)

    providers = providers.drop(["last_updated", "timezone", "language", "operator", "ttl", "purchase_url", "url"], axis = 1)

    rename_cols = {
        "provider_id" : "provider_id",
        "name" : "provider name",
        "vehicle_type" : "vehicle type",
        "rental_apps" : "provider apps",
        "email" : "provider email",
        "phone_number" : "provider phone"
    }
    providers.set_index("provider_id", inplace = True)


    providers.rename(columns = rename_cols, inplace=True)


    ## get stations

    stations = client.request_feed('station_information').get('data').get('stations')
    stations = pd.DataFrame(stations)

    stations = stations.drop(["post_code", "rental_uris", "short_name", "address"], axis = 1)

    rename_cols = {
        "region_id" : "region_id",
        "station_id" : "station_id",
        "name" : "vehicle or station name",
        "lat" : "latitude",
        "lon" : "longitude",
    }

    stations.rename(columns = rename_cols, inplace=True)

    stations.set_index("provider_id", inplace = True)
    
    stations_providers = pd.merge(stations, providers, left_index=True, right_index=True, how="left")
    stations_providers = stations_providers[["provider name", "vehicle or station name", "vehicle type", "station_id","provider apps", "provider email", "provider phone", "latitude", "longitude"]]
    
    ## get station status

    station_status = client.request_feed("station_status").get("data").get("stations")
    station_status = pd.DataFrame(station_status)
    rename_cols = {
        "num_bikes_available" : "number of available vehicles (station)",
        "name" : "vehicle name",
        "lat" : "latitude",
        "lon" : "longitude",
    }
    station_status.rename(columns = rename_cols, inplace=True)

    station_status.set_index("station_id", inplace = True)
    station_status = station_status.drop(["provider_id", "num_docks_available", "last_reported", "is_installed", "is_returning"], axis = 1)

    stations_providers.reset_index(inplace = True)
    stations_providers.set_index("station_id", inplace = True)

    stations_providers = pd.merge(stations_providers, station_status, left_index=True, right_index=True, how="left")
    
    # get system pricing plans-------------------

    system_pricing_plans = client.request_feed("system_pricing_plans").get("data").get("plans")
    system_pricing_plans = pd.DataFrame(system_pricing_plans)
    system_pricing_plans = system_pricing_plans.drop(["plan_id", "url", "is_taxable", "price", "currency"], axis = 1)
    system_pricing_plans["description"] = np.where(system_pricing_plans["description"].str.startswith('Lorem ipsum'), np.nan, system_pricing_plans["description"])
    rename_cols = {
        "provider_id" : "provider_id",
        "name" : "pricing plan name",
        "description" : "pricing",
    }
    system_pricing_plans.rename(columns = rename_cols, inplace=True)

    system_pricing_plans = system_pricing_plans.groupby("provider_id", as_index=False).agg(lambda x: next((val for val in x if not pd.isnull(val)), np.nan))


    system_pricing_plans.set_index("provider_id", inplace = True)
    
    stations_providers.reset_index(inplace = True)
    stations_providers.set_index("provider_id", inplace = True)

    stations_providers = pd.merge(stations_providers, system_pricing_plans, left_index=True, right_index=True, how="left")


    # get geofencing zones--------------------

    geofencing_zones = client.request_feed("geofencing_zones").get("data").get("geofencing_zones").get("features")
    geofencing_zones = pd.DataFrame(geofencing_zones)

    status = client.request_feed("free_bike_status").get("data").get("bikes")
    status = pd.DataFrame(status)
    status.set_index("bike_id", inplace = True)
    status = status.drop("rental_uris", axis = 1)
    
    ## get bike status
    stations_providers.reset_index(inplace = True)
    stations_providers.set_index("station_id", inplace= True)
    stations_providers = pd.merge(stations_providers, status, left_index=True, right_index=True, how="left")

    stations_providers.reset_index(inplace = True)
    stations_providers = stations_providers.drop(["provider_id_x", "station_id", "provider_id_y"], axis = 1)
    ai_file = stations_providers
    
    st.success("Data loaded successfully!")



# Function to create an interactive map
def create_interactive_map(geo_df):
    # Create a FastMarkerCluster for faster loading
    fm = FastMarkerCluster(data=list(zip(geo_df['latitude'], geo_df['longitude'])))

    # Create a satellite map with a placeholder attribution
    m = folium.Map(
        location=[46.8182, 8.2275],
        zoom_start=8,
        tiles='https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
        attr='OpenStreetMap',
    )

    # Add FastMarkerCluster to the map
    m.add_child(fm)

    # Add GeoDataFrame points to the FastMarkerCluster
    for _, station in geo_df.iterrows():
        folium.Marker([station['latitude'], station['longitude']], popup=station['vehicle or station name'], icon=folium.Icon(color='white', icon_size=(10, 10))).add_to(fm)

    return m



# Set a default value for the select box
selected_region = st.selectbox("To further help you, first choose your preferred vehicle type", [""] + list(set(ai_file["vehicle type"])))

# Check if something is selected
if selected_region:
    filtered_stations = ai_file[ai_file["vehicle type"] == selected_region]
    provider_name = st.selectbox("Filter for your preferred provider", [""] + list(set(filtered_stations["provider name"])))

    if provider_name:
        filtered_stations = filtered_stations[filtered_stations["provider name"] == provider_name]
        # Display the filtered DataFrame
        st.write("Filtered Stations:")
        

        station_df = filtered_stations

        # Create a GeoDataFrame from the DataFrame
        geometry = [Point(longitude, latitude) for longitude, latitude in zip(station_df['longitude'], station_df['latitude'])]
        geo_df = gpd.GeoDataFrame(station_df, geometry=geometry, crs="EPSG:4326")

        # Filter points that are within Switzerland
        switzerland_geojson_path = 'switzerland.geojson'
        switzerland = gpd.read_file(switzerland_geojson_path)
        geo_df = gpd.sjoin(geo_df, switzerland, op='within')

        # Create and display the interactive map
        st.subheader("Interactive Map of Stations:")
        folium_map = create_interactive_map(geo_df)
        folium_static(folium_map)


    
        prompt = """Prompt for Extended Shared Mobility Chatbot Instructions (Updated Dataset):

        "Objective: You are a Shared Mobility Chatbot designed to efficiently provide information about available shared mobility vehicles in Switzerland based on the new dataset.

        New Dataset Overview:

        Columns: station_id, provider, name, vehicle_type, provider_apps, provider_email, provider_phone, latitude, longitude, is_renting, num_available_vehicles, pricing_plan_name, pricing.
        Instructions:

        Greetings and Introduction:
        Greet users warmly and introduce yourself as the Shared Mobility Chatbot for Switzerland.
        Clearly state your purpose: to assist with information about shared mobility vehicles.
        Encourage Queries:
        Encourage users to ask questions related to vehicle availability, types, providers, regions, and station IDs.
        Use phrases like "Feel free to explore and ask anything related to shared mobility in Switzerland. I'm here to help! 🚗🛴"
        Efficiency Tips:
        Respond swiftly to user queries to ensure a seamless experience.
        Use parallel processing to simultaneously check for multiple data points, enhancing speed.
        Example Queries and Answers:
        a. User Query: "What vehicles does [Provider] offer in [Region]?"
        Response: Retrieve and list vehicle details from the specified provider in the requested region.
        b. User Query: "Tell me about the [Vehicle Type] available in [City]."
        Response: Provide details about the specified vehicle type in the requested city.
        c. User Query: "Give me details about the station with ID [Station ID]."
        Response: Fetch and present comprehensive details about the specified station ID.
        FAQs and Efficient Responses:
        a. FAQ: "How do I rent a vehicle?"
        Response: Provide a brief overview and direct users to the provider_apps for the specified provider.
        b. FAQ: "Can you recommend a reliable provider in [Region]?"
        Response: Recommend a provider based on the region_id, including their contact information.
        c. FAQ: "What vehicle types are commonly available in Switzerland?"
        Response: Summarize common vehicle types using information from the dataset.
        Data Retrieval:
        Efficiently use the dataset to retrieve relevant information based on user queries.
        Cross-reference user input with dataset columns for accurate responses.
        Formatting Responses:
        Present information in a clear, organized manner, including vehicle name, type, location coordinates, and operator details.
        Closing:
        Conclude conversations with a positive note, inviting users to ask more questions.
        Example Closing Phrase: "Feel free to explore and ask anything related to shared mobility in Switzerland. I'm here 24/7 to assist you! 🚗🛴"""
        
        
        
        # Initiate Open AI Assistant--------------------------------------------------------------------------------

        # Initialize session state variables for file IDs and chat control

        if "file_id_list" not in st.session_state:
            st.session_state.file_id_list = []

        if "start_chat" not in st.session_state:
            st.session_state.start_chat = False

        if "thread_id" not in st.session_state:
            st.session_state.thread_id = None

        from openai import OpenAI

        ai_client = OpenAI(api_key="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")

        assistant = ai_client.beta.assistants.create(
            name="Shared Mobility Retrieval Assistant",
            instructions= prompt,
            model="gpt-4-1106-preview",
            tools=[{"type": "retrieval"}]
        )

        # Create a Open AI Thread--------------------

        thread = ai_client.beta.threads.create()

        # Connect Thread to our new Assistant--------------------

        run = ai_client.beta.threads.runs.create(
        thread_id=thread.id,
        assistant_id=assistant.id,
        )

        messages = ai_client.beta.threads.messages.list(thread_id=thread.id)


        # Now we finally give our Assistant a Name--------------------

        SHARED_MOBILITY_ASSISTANT_ID = assistant.id

        ai_client = OpenAI(api_key="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")

        # Some other Functions--------------------


        def submit_message(assistant_id, thread, user_message):
            ai_client.beta.threads.messages.create(
            thread_id=thread.id, role="user", content=user_message
            )
            return ai_client.beta.threads.runs.create(
                thread_id=thread.id,
                assistant_id=assistant.id,
            )
        def get_response(thread):
            return ai_client.beta.threads.messages.list(thread_id=thread.id, order="asc")
        def create_thread_and_run(user_input):
            thread = ai_client.beta.threads.create()
            run = submit_message(SHARED_MOBILITY_ASSISTANT_ID, thread, user_input)
            return thread, run
        def pretty_print(messages):
            print("# Messages")
            for m in messages:
                print(f"{m.role}: {m.content[0].text.value}")
            print()
        def wait_on_run(run, thread):
            while run.status == "queued" or run.status == "in_progress":
                run = ai_client.beta.threads.runs.retrieve(
                    thread_id=thread.id,
                    run_id=run.id,
                )
                time.sleep(0.5)
            return run

        # Connect the Assistant with our DataFrame--------------------
        
        # Add a spinner until the data is uploaded to the assistant
        with st.spinner("Initiating your Assistant"):
            import io
            import requests

            # Read the JSON file and perform some transformations

            file = filtered_stations

            # Write the DataFrame to an in-memory JSON file

            output = io.BytesIO()
            file.to_json(output)
            json_data = output.getvalue()

            # Convert the JSON data to a file-like object

            json_file_like = io.BytesIO(json_data)

            # Upload the file

            file = ai_client.files.create(
            file=json_file_like,
            purpose="assistants",
            )

            # Update Assistant

            assistant = ai_client.beta.assistants.update(
                SHARED_MOBILITY_ASSISTANT_ID,
                tools=[{"type": "code_interpreter"}, {"type": "retrieval"}],
                file_ids=[file.id],
            )      
        st.success("Initiated successfully!")

        st.session_state.start_chat = True
        # Create a thread once and store its ID in session state

        thread = ai_client.beta.threads.create()
        st.session_state.thread_id = thread.id
        st.write("thread id: ", thread.id)

        # Define the function to process messages with citations

        def process_message_with_citations(message):
            """Extract content and annotations from the message and format citations as footnotes."""
            message_content = message.content[0].text
            annotations = message_content.annotations if hasattr(message_content, 'annotations') else []
            citations = []

            # Iterate over the annotations and add footnotes
            for index, annotation in enumerate(annotations):
                # Replace the text with a footnote
                message_content.value = message_content.value.replace(annotation.text, f' [{index + 1}]')

                # Gather citations based on annotation attributes
                if (file_citation := getattr(annotation, 'file_citation', None)):
                    # Retrieve the cited file details (dummy response here since we can't call OpenAI)
                    cited_file = {'filename': 'cited_document.pdf'}  # This should be replaced with actual file retrieval
                    citations.append(f'[{index + 1}] {file_citation.quote} from {cited_file["filename"]}')
                elif (file_path := getattr(annotation, 'file_path', None)):
                    # Placeholder for file download citation
                    cited_file = {'filename': 'downloaded_document.pdf'}  # This should be replaced with actual file retrieval
                    citations.append(f'[{index + 1}] Click [here](#) to download {cited_file["filename"]}')  # The download link should be replaced with the actual download path

            # Add footnotes to the end of the message content
            full_response = message_content.value + '\n\n' + '\n'.join(citations)
            return full_response
        # Main chat interface setup
        st.title("OpenAI Assistants API Chat")
        st.write("This is a simple chat application that uses OpenAI's API to generate responses.")


        # Only show the chat interface if the chat has been started

        if st.session_state.start_chat:

            # Initialize the model and messages list if not already in session state

            if "openai_model" not in st.session_state:
                st.session_state.openai_model = "gpt-4-1106-preview"
            if "messages" not in st.session_state:
                st.session_state.messages = []

            # Display existing messages in the chat
            for message in st.session_state.messages:
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])

            # Chat input for the user
            if prompt := st.chat_input("What is up?"):
                # Add user message to the state and display it
                st.session_state.messages.append({"role": "user", "content": prompt})
                with st.chat_message("user"):
                    st.markdown(prompt)

                # Add the user's message to the existing thread
                ai_client.beta.threads.messages.create(
                    thread_id=st.session_state.thread_id,
                    role="user",
                    content=prompt
                )

                # Create a run with additional instructions
                run = ai_client.beta.threads.runs.create(
                    thread_id=st.session_state.thread_id,
                    assistant_id=assistant.id,
                    instructions="Please answer the queries using the knowledge provided in the files.When adding other information mark it clearly as such.with a different color"
                )

                # Poll for the run to complete and retrieve the assistant's messages
                while run.status != 'completed':
                    time.sleep(1)
                    run = ai_client.beta.threads.runs.retrieve(
                        thread_id=st.session_state.thread_id,
                        run_id=run.id
                    )

                # Retrieve messages added by the assistant
                messages = ai_client.beta.threads.messages.list(
                    thread_id=st.session_state.thread_id
                )

                # Process and display assistant messages
                assistant_messages_for_run = [
                    message for message in messages 
                    if message.run_id == run.id and message.role == "assistant"
                ]
                for message in assistant_messages_for_run:
                    full_response = process_message_with_citations(message)
                    st.session_state.messages.append({"role": "assistant", "content": full_response})
                    with st.chat_message("assistant"):
                        st.markdown(full_response, unsafe_allow_html=True)
        else:
            # Prompt to start the chat
            st.write("Please upload files and click 'Start Chat' to begin the conversation.")
        sys.exit("Exiting the code with sys.exit()!")
        
        thread, run = create_thread_and_run("what is the cheapest shared mobility service?")
        run = wait_on_run(run, thread)
        messages = get_response(thread)

        # Display the messages in the Streamlit app
        st.write("Chatbot Response:")
        for message in messages:
            st.write(f"{message.role}: {message.content[0].text.value}")

#-----------------------------------------------------------------------------------------------
