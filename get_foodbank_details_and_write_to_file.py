import requests
import ast
import time
from bs4 import BeautifulSoup

def show_items_needed_by_foodbank(foodbank_give_food_page_url): # Takes a foodbank's "give food" page URL, and returns a list of items needed by that foodbank
	items_needed = []
	try:
		r = requests.get(foodbank_give_food_page_url)
	except: # Handle exceptions, e.g. the request library uncovering an SSL problem with a site
		return("Request failed. Likely an SSL certificate error")
	else:
		if ((r.status_code != 200) and (r.status_code != 304)): # If status code is neither 200 nor 304
			return("Bad status code")
		soup = BeautifulSoup(r.text, "lxml")
		ul_with_first_shopping_list = soup.find_all("ul", class_="page-section--sidebar__block-shopping-list", limit=1) # Only return the first 1
		if (not ul_with_first_shopping_list): # If no items were found, although the assumed give food page URL returned a good status code
			return("No items found")
		lis_of_first_shopping_list = ul_with_first_shopping_list[0].find_all("li") # Need to specify the index, even though it's a single item result set https://stackoverflow.com/questions/24108507/beautiful-soup-resultset-object-has-no-attribute-find-all
		for desired_item in lis_of_first_shopping_list:
			desired_item_in_unicode = str(desired_item.string)
			items_needed.append(desired_item_in_unicode) # Convert to unicode for more efficient memory use, as per https://www.crummy.com/software/BeautifulSoup/bs4/doc/#navigablestring
		return items_needed

response = requests.get("https://www.trusselltrust.org/get-help/find-a-foodbank/foodbank-search/?foodbank_s=all&callback=?")
if ((response.status_code == 200) or (response.status_code == 304)):
    print('Successful response from server')
else:
	print("Bad response from server")
print("")

trimmed_response_string = response.text[2:-2] # response.content would be in bytes. response.text gives a string. Trim the top and tail, to just give the list.
trimmed_response_string = trimmed_response_string.replace("false", "False") # Capitalise so Python understands the boolean 
trimmed_response_string = ast.literal_eval(trimmed_response_string) # Interrogate the string value as a variable - hopefully a list of dictionary objects. May cause stack overflow if too complex

number_of_foodbanks = 0 # Including nonconforming ones
number_of_nonconforming_foodbanks = 0 # A.K.A. "poorly" or "non-standard" food banks. Their website doesn't work, or are different to the usual model.

# Create a dictionary, with each foodbank name as a key to its own dictionary object
# {address, latitude, longitude, website, donate_food_url, food needed (only populated if we successfully got this information), error (only populated if there was a problem getting the information)}
dictionary_of_foodbanks_and_information = {}

for foodbank in trimmed_response_string:
	#if (foodbank['foodbank_information']['name'][0] == "B"): ## We work through foodbanks alphabetically. Stop at the start of the given letter. For debugging
	#	break
	number_of_foodbanks += 1
	print(foodbank['foodbank_information']['name'])
	if (not foodbank['foodbank_information']['website']): # If this foodbank doesn't have a website, add it, but without website or items needed info
		dictionary_of_foodbanks_and_information[foodbank['foodbank_information']['name']] = {"address" : foodbank['foodbank_information']['geolocation']['address'], "latitude" : foodbank['foodbank_information']['geolocation']['lat'], "longitude" : foodbank['foodbank_information']['geolocation']['lng'], "website" : "", "error" : "No website given by master list", "location_type" : "foodbank"}
		number_of_nonconforming_foodbanks += 1
	else:
		if (foodbank['foodbank_information']['website'][-1] == "/"): # Handle the URL, whether its given with a trailing slash or not
			likely_donate_food_page_url = foodbank['foodbank_information']['website'] + "give-help/donate-food/"
		else:
			likely_donate_food_page_url = foodbank['foodbank_information']['website'] + "/give-help/donate-food/"
		tidied_likely_donate_food_page_url = likely_donate_food_page_url.replace("\\", "") # Need to put backslash twice because it's an escape character
		items_needed_by_this_foodbank = show_items_needed_by_foodbank(tidied_likely_donate_food_page_url)	
		if type(items_needed_by_this_foodbank) == str: # If an error (string) was returned for this foodbank, instead of a list of items, record the foodbank with this information
			number_of_nonconforming_foodbanks += 1			
			if (items_needed_by_this_foodbank == "Request failed. Likely an SSL certificate error"):
				dictionary_of_foodbanks_and_information[foodbank['foodbank_information']['name']] = {"address" : foodbank['foodbank_information']['geolocation']['address'], "latitude" : foodbank['foodbank_information']['geolocation']['lat'], "longitude" : foodbank['foodbank_information']['geolocation']['lng'], "website" : "", "error" : items_needed_by_this_foodbank, "location_type" : "foodbank"} # Like the other cases of errors, but in this case we hide the website because there might be a security issue
			else:
				dictionary_of_foodbanks_and_information[foodbank['foodbank_information']['name']] = {"address" : foodbank['foodbank_information']['geolocation']['address'], "latitude" : foodbank['foodbank_information']['geolocation']['lat'], "longitude" : foodbank['foodbank_information']['geolocation']['lng'], "website" : foodbank['foodbank_information']['website'], "error" : items_needed_by_this_foodbank, "location_type" : "foodbank"} # Don't populate items needed as we don't know what they are.
		if type(items_needed_by_this_foodbank) == list:
			dictionary_of_foodbanks_and_information[foodbank['foodbank_information']['name']] = {"address" : foodbank['foodbank_information']['geolocation']['address'], "latitude" : foodbank['foodbank_information']['geolocation']['lat'], "longitude" : foodbank['foodbank_information']['geolocation']['lng'], "website" : foodbank['foodbank_information']['website'], "items_needed" : items_needed_by_this_foodbank, "location_type" : "foodbank"} # Add this foodbank's information to the dictionary of foodbanks, as a dictionary itself
	if (foodbank['foodbank_centre'] != False): # If the foodbank has child foodbank centres
		# It looks like items needed and website are the same as the overall foodbank.
		# Its name, telephone number, opening times, and various address values, are specific
		dictionary_of_foodbanks_and_information[foodbank['foodbank_information']['name']]['foodbank_centres'] =  [] # Initialise empty list, to contain names of child foodbank centres
		for foodbank_centre in foodbank['foodbank_centre']:
			if (('foodbank_name' in foodbank_centre) and ('address' in foodbank_centre['centre_geolocation']) and ('lat' in foodbank_centre['centre_geolocation']) and ('lng' in foodbank_centre['centre_geolocation'])): # Check that all the expected values are present for this foodbank centre
				if type(items_needed_by_this_foodbank) == str: # As above. If a foodbank centre's child foodbank has an error or no website, store it differently.
					number_of_nonconforming_foodbanks += 1			
					if (items_needed_by_this_foodbank == "Request failed. Likely an SSL certificate error"):
						if (foodbank_centre['foodbank_name'] in dictionary_of_foodbanks_and_information): # If the foodbank centre name is the same as an existing foodbank name, append 'foodbank centre' to the end. To avoid a key clash 
							dictionary_of_foodbanks_and_information[foodbank_centre['foodbank_name'] + ' foodbank centre'] = {"address" : foodbank_centre['centre_geolocation']['address'], "latitude" : foodbank_centre['centre_geolocation']['lat'], "longitude" : foodbank_centre['centre_geolocation']['lng'], "website" : "", "error" : items_needed_by_this_foodbank,  "location_type" : "foodbank_centre", "parent_foodbank" : foodbank['foodbank_information']['name']}
							dictionary_of_foodbanks_and_information[foodbank['foodbank_information']['name']]['foodbank_centres'].append(foodbank_centre['foodbank_name'] + " foodbank centre") # Record this foodbank centre as a child in the entry for its parent foodbank
						else:
							dictionary_of_foodbanks_and_information[foodbank_centre['foodbank_name']] = {"address" : foodbank_centre['centre_geolocation']['address'], "latitude" : foodbank_centre['centre_geolocation']['lat'], "longitude" : foodbank_centre['centre_geolocation']['lng'], "website" : "", "error" : items_needed_by_this_foodbank, "location_type" : "foodbank_centre", "parent_foodbank" : foodbank['foodbank_information']['name']}
							dictionary_of_foodbanks_and_information[foodbank['foodbank_information']['name']]['foodbank_centres'].append(foodbank_centre['foodbank_name']) # Record this foodbank centre as a child in the entry for its parent foodbank
					else:
						if (foodbank_centre['foodbank_name'] in dictionary_of_foodbanks_and_information):
							dictionary_of_foodbanks_and_information[foodbank_centre['foodbank_name']  + ' foodbank centre'] = {"address" : foodbank_centre['centre_geolocation']['address'], "latitude" : foodbank_centre['centre_geolocation']['lat'], "longitude" : foodbank_centre['centre_geolocation']['lng'], "website" : foodbank['foodbank_information']['website'], "error" : items_needed_by_this_foodbank, "location_type" : "foodbank_centre", "parent_foodbank" : foodbank['foodbank_information']['name']}					
							dictionary_of_foodbanks_and_information[foodbank['foodbank_information']['name']]['foodbank_centres'].append(foodbank_centre['foodbank_name']  + " foodbank centre")
						else:
							dictionary_of_foodbanks_and_information[foodbank_centre['foodbank_name']] = {"address" : foodbank_centre['centre_geolocation']['address'], "latitude" : foodbank_centre['centre_geolocation']['lat'], "longitude" : foodbank_centre['centre_geolocation']['lng'], "website" : foodbank['foodbank_information']['website'], "error" : items_needed_by_this_foodbank, "location_type" : "foodbank_centre", "parent_foodbank" : foodbank['foodbank_information']['name']}					
							dictionary_of_foodbanks_and_information[foodbank['foodbank_information']['name']]['foodbank_centres'].append(foodbank_centre['foodbank_name'])
				if type(items_needed_by_this_foodbank) == list:
					if (foodbank_centre['foodbank_name'] in dictionary_of_foodbanks_and_information):
						dictionary_of_foodbanks_and_information[foodbank_centre['foodbank_name'] + ' foodbank centre'] = {"address" : foodbank_centre['centre_geolocation']['address'], "latitude" : foodbank_centre['centre_geolocation']['lat'], "longitude" : foodbank_centre['centre_geolocation']['lng'], "website" : foodbank['foodbank_information']['website'], "items_needed" : items_needed_by_this_foodbank, "location_type" : "foodbank_centre", "parent_foodbank" : foodbank['foodbank_information']['name']}					
						dictionary_of_foodbanks_and_information[foodbank['foodbank_information']['name']]['foodbank_centres'].append(foodbank_centre['foodbank_name'] + " foodbank centre")
					else:
						dictionary_of_foodbanks_and_information[foodbank_centre['foodbank_name']] = {"address" : foodbank_centre['centre_geolocation']['address'], "latitude" : foodbank_centre['centre_geolocation']['lat'], "longitude" : foodbank_centre['centre_geolocation']['lng'], "website" : foodbank['foodbank_information']['website'], "items_needed" : items_needed_by_this_foodbank, "location_type" : "foodbank_centre", "parent_foodbank" : foodbank['foodbank_information']['name']}					
						dictionary_of_foodbanks_and_information[foodbank['foodbank_information']['name']]['foodbank_centres'].append(foodbank_centre['foodbank_name'])
			else: #If we don't have the all the expected pieces of information about this foodbank's child foodbank centres
				number_of_nonconforming_foodbanks += 1
				continue ## If this foodbank centre has doesn't have all the information we need, skip it. TODO think of what we might do here.
		#print(dictionary_of_foodbanks_and_information[foodbank['foodbank_information']['name']]['foodbank_centres'])
	else:
		dictionary_of_foodbanks_and_information[foodbank['foodbank_information']['name']]['foodbank_centres'] =  False # Record that this foodbank does not have child foodbank centres
	time.sleep(10) # Avoid hammering the server too aggressively.

	
print("Finished iterating through the list of foodbanks")
print("Number of foodbanks in total: " + str(number_of_foodbanks))
print("Number of nonconforming foodbanks: " + str(number_of_nonconforming_foodbanks))
print("")
for foodbank_name in dictionary_of_foodbanks_and_information:
	print(foodbank_name)
	print(dictionary_of_foodbanks_and_information[foodbank_name])
	print("")

with open("foodbank_data_storage.txt", "w") as data_storage_file:
	data_storage_file.write(str(dictionary_of_foodbanks_and_information))
	print("Information written to file")
