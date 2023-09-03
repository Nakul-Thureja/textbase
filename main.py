from textbase import bot, Message
from textbase.models import OpenAI
from tabulate import tabulate
from typing import List
import json
import pandas as pd

# Load your OpenAI API key
OpenAI.api_key = ""

# Prompt for GPT-3.5 Turbo
SYSTEM_PROMPT_PARSER = """
You are a input parser, 
you don't know anything about travel planning and only used for parsing user data therfore should not give any suggestions, 
your only task is to enquire about the source and destination city, travel date and number of days from the user.
Date should be in format "yyyy-mm-dd" and default year should 2023
Your only output should be only json,
{
"source_city" 
 "destination_city"
"date" 
"day"
} do not engage in a conversation 
"""

SYSTEM_PROMPT_DECIDER = """
You are a simple destination decider for users. Greet the user well and be friendly.
you only have information about these cities
["Delhi", "Mumbai", "Chennai", "Kolkata", "Bengaluru", "Hyderabad", "Pune", "Jaipur", "Ahmedabad", "Lucknow"] .
If user wants to travel to some other place then say sorry.
Only use this phrase "Enjoy your trip to" once you have confirmed the destination from user else continue to help them decide.
"""

SYSTEM_PROMPT_ADVISOR = """
You are a professional travel planner,
you will be given a city and destination help craft a itenary for a user on their preferences.
Be helpful and friendly.
Don't mention hotel or flights yourself. You should only return "Sorry" if asked about hotel or flights nothing else and you shouldn't use the word sorry in any other case.
"""


# read data from the dataset
indian_cities = ["Delhi", "Mumbai", "Chennai", "Kolkata", "Bengaluru", "Hyderabad", "Pune", "Jaipur", "Ahmedabad", "Lucknow"]
flight_data = pd.read_csv('Indian_flights.csv')
hotel_data = pd.read_csv('Indian_hotels.csv')

        
@bot()
def on_message(message_history: List[Message], state: dict = None):
    # Load the JSON data from the file
    with open("data.json", "r") as json_file:
        data = json.load(json_file)

    # Access the variables
    source_city = data["source_city"]
    destination_city = data["destination_city"]
    date = data["date"]
    days = data["days"] 

    if not destination_city:
        # Generate GPT-3.5 Turbo response
        bot_response = OpenAI.generate(
            system_prompt=SYSTEM_PROMPT_DECIDER,
            message_history=message_history, # Assuming history is the list of user messages
            model="gpt-3.5-turbo",
        )
        if "Enjoy your trip to" in bot_response:
            for city in indian_cities:
                if city in bot_response:
                    destination_city = city
                    data = {}
                    data["source_city"] = None
                    data["destination_city"] = destination_city
                    data["date"] = None
                    data["days"] = None

                    # Write the data to the JSON file
                    with open("data.json", "w") as json_file:
                        json.dump(data, json_file)

                    break
            bot_response += "\n For more help please provide \n\n\n\n1.Source City\n\n\n\n2.Destination City\n\n\n\n3.Date of Departure\n\n\n\n4.Days\n\n\n\nmake sure they are all present in your response "  

    elif not date:
        # Generate GPT-3.5 Turbo response
        bot_response = OpenAI.generate(
            system_prompt=SYSTEM_PROMPT_PARSER,
            message_history=message_history, # Assuming history is the list of user messages
            model="gpt-3.5-turbo",
        )
        if '{' in bot_response:
            start_index = bot_response.find("{")
            end_index = bot_response.find("}")
            json_object = json.loads( bot_response[ start_index : end_index+1 ] )
            source_city = json_object[ "source_city" ]
            destination_city = json_object[ "destination_city" ]
            date = json_object[ "date" ]

            # Write the data to the JSON file
            with open("data.json", "w") as json_file:
                json.dump(json_object, json_file)
            
            prompt = "Itenary for {}".format(json_object)

            bot_response = "GREAT!!\n\n"
            bot_response += OpenAI.generate(
                system_prompt=SYSTEM_PROMPT_ADVISOR,
                message_history=[{'role': 'user', 'content': [{'data_type': 'STRING', 'value': prompt }]}], # Assuming history is the list of user messages
                model="gpt-3.5-turbo",
            )
        
    else:
        bot_response = OpenAI.generate(
            system_prompt=SYSTEM_PROMPT_ADVISOR,
            message_history=message_history, # Assuming history is the list of user messages
            model="gpt-3.5-turbo",
        )

    # add data for flight and hotels
    with open("data.json", "r") as json_file:
        data = json.load(json_file)
    if data[ 'source_city' ]:
        # Filter the DataFrame based on the given cities and date
        filtered_flight_data = flight_data[
            (flight_data['Source'] == source_city) &
            (flight_data['Destination'] == destination_city) &
            (flight_data['Date'].str.startswith(date))
            ]
        
        filtered_hotel_data = hotel_data[
            (hotel_data['City'] == destination_city)
        ]
        
        bot_response += f"\n\n\n\nHere are some flights from {source_city} to {destination_city}\n\n\n\n" + "{}".format(tabulate(filtered_flight_data, headers='keys', tablefmt='pretty', showindex=False))
        bot_response += f"\n\n\n\nHere are some Hotels in {destination_city}\n\n\n\n" + "{}".format(tabulate(filtered_hotel_data, headers='keys', tablefmt='pretty', showindex=False))
        bot_response += "\n\n\n\nAs of now, We don't have the functionality to book these"
                
    response = {
        "data": {
            "messages": [
                {
                    "data_type": "STRING",
                    "value": bot_response
                }
            ],
            "state": state
        },
        "errors": [
            {
                "message": ""
            }
        ]
    }
    
    print(response)
    return {
        "status_code": 200,
        "response": response
    }