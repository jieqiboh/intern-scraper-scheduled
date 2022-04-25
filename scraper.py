#Connect to database and return client object
import pymongo
from pymongo import MongoClient
from bs4 import BeautifulSoup
import requests
import re
conn_str = "mongodb+srv://admin:admin@cluster0.6ejza.mongodb.net/myFirstDatabase?retryWrites=true&w=majority"
client = MongoClient(conn_str)

job_ids_collection = client["mydatabase"]["job_ids"]
company_collection = client["mydatabase"]["company"]
title_collection = client["mydatabase"]["title"]
period_collection = client["mydatabase"]["period"]
job_type_collection = client["mydatabase"]["job_type"]
profession_category_collection = client["mydatabase"]["profession_category"]
industry_category_collection = client["mydatabase"]["industry_category"]

company_list = list(key['item'] for key in company_collection.find({},{"_id":0}))
title_list = list(key['item'] for key in title_collection.find({},{"_id":0}))
period_list = list(key['item'] for key in period_collection.find({},{"_id":0}))
job_type_list = list(key['item'] for key in job_type_collection.find({},{"_id":0}))
profession_category_list = list(key['item'] for key in profession_category_collection.find({},{"_id":0}))
industry_category_list = list(key['item'] for key in industry_category_collection.find({},{"_id":0}))

#keywords to search
#Keywords in their entirety have to be found in the get_text() area. Keywords can be modified and stored
#Keywords are categorised into the following types
#Must-have keywords are those that must have at least 1 appearance in text (dealbreakers), which are period and job_type
#Optional keywords are company and title that are filtered after must-haves
company = company_list
title = title_list
period = period_list #Must have at least 1 suitable period
job_type = job_type_list #Must have at least 1 suitable job_type
optional = company+title

#Links
#Filter by profession
Profession = profession_category_list
#Filter By industry
Industry = industry_category_list

#Take jobs list soup and returns links to jobs that meet criteria#
#Get jobs-list and convert to soup
def jobs_list_filter(soup):
    jobs_list = soup.findAll('div', class_="jobs-list")
    jobs_list_soup = BeautifulSoup(str(jobs_list), "html.parser")
    #Get job postings by classname and concatenate all into list of elements
    jobs_list_children_even = jobs_list_soup.select('div.ast-row.list-even')
    jobs_list_children_odd = jobs_list_soup.select('div.ast-row.list-odd')
    jobs_list_children = jobs_list_children_even+jobs_list_children_odd

    #checks if any keyword exists in the text of the job
    arr = ['company name','title','location','period','job type']
    found = []
    for child in jobs_list_children:
        text = child.get_text()
        for p in period: #Filter out period
            if p in text:
                for j in job_type: #Filter out job_type
                    if j in text:
                        for kw in optional: #Then scan for title and companies with optional
                            if kw in text:
                                found.append(child.a['href'])
    return found

#Takes a link to a page and returns id and dictionary of info regarding job#
#Note keywords to be filtered out if webpage changes!
#get div containing important contents and get_text()
def job_data_filter(joblink):
    jobpage = requests.get(joblink)
    soup = BeautifulSoup(jobpage.text, "html.parser")
    #Get stripped strings of text in detail container and parse based on company, designation etc
    details = list(soup.find('div', class_="isg-detail-container").stripped_strings)
    #Get header and job id
    header = soup.find('nav', role="navigation")
    job_id = int(header.get_text().split("Job ID:")[1]) #get numbers to the right of job id

    job_data = {}
    job_data["job_id"]=job_id
    for idx,elem in enumerate(details):
        if elem=="Company" or elem=="Designation" or elem=="Date Listed" or elem=="Job Type" or elem=="Job Period":
            job_data[elem]=details[idx+1] #Add company name

    return job_data

import telegram
TOKEN = '5285656526:AAFAL9iXqQf-8XToM0nnEByG46zfQ2Rmmq8'
bot = telegram.Bot(token=TOKEN)
chatid = 1084702879

#takes a list of links and scrapes according to filters, and adds new entries to mongodb
#Also checks if joblinks appeared before by comparing id, then sends the details to telegram bot to output
def scrapeLinksWithFilter(lst):
    for link in lst:
        page = requests.get(link)
        soup = BeautifulSoup(page.text, "html.parser")
        
        found_jobs = jobs_list_filter(soup)
        
        for joblink in found_jobs:
            job_details = job_data_filter(joblink)
            #search mongodb job_ids collection by "job_id" to see if id already exists
            find_job = job_ids_collection.find_one({'job_id':job_details['job_id']})
            #if not exist,
            #insert into mongodb job_ids collection
            #send formatted text to telegram hook
            
            if not find_job:
                job_id = job_details.pop('job_id', None)
                job_ids_collection.insert_one({'job_id':job_id,'job_details':job_details})
                #send to telegram hook
                msg = ""
                for item in job_details.items():
                    msg+=item[0]+": "+item[1]+"\n"
                bot.send_message(chat_id=chatid,text=msg)
            else:
                continue

scrapeLinksWithFilter(Industry)
scrapeLinksWithFilter(Profession)