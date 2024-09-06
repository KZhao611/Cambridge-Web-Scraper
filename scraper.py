from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import StaleElementReferenceException
from concurrent.futures import ThreadPoolExecutor, as_completed
from enum import Enum
import requests
import time
import pandas as pd

class CitationStyle(Enum):
    AMA = "american-medical-association"
    APSA = "american-political-science-association"
    APA = "apa"
    CHICAGO = "chicagob"
    HARVARD = "harvard"
    IEEE = "ieee"
    MHRA = "modern-humanities-research-association"
    MLA = "mla7"
    VANCOUVER = "vancouver"

#To click the cite button, idk but it only works when i use this
def click_element(driver, by, value):
    max_attempts = 3
    for attempt in range(max_attempts):
        try:
            element = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((by, value))
            )
            time.sleep(0.5)
            element.click()
            break  # Exit the loop if successful
        except StaleElementReferenceException:
            # print(f"Attempt {attempt + 1} failed. Retrying...")
            time.sleep(.5)  # Backoff before retrying


#Get Abstract and Chicago Citation from link
def get_info(link, citation_style):
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # Enable headless mode
    chrome_options.add_argument("--no-sandbox")  # For environments where sandboxing is not available
    chrome_options.add_argument("--log-level=3")
    driver = webdriver.Chrome(options=chrome_options)
    driver.get(link)
    page_source = driver.page_source
    soup = BeautifulSoup(page_source, 'html.parser')

    try:
        s = soup.find('div', class_='abstract')
        abstract = s.text
    except Exception as e:
        print("error at abstract")
        raise e

    # print(button)
    click_element(driver, By.LINK_TEXT, "Show author details")
    s = soup.find_all('div', class_='row author')
    authors = []

    try:
        for row in s:
            authors.append(row.text.strip().split(' Affiliation: ')[1])
    except Exception as e:
        print("error at authors")
        raise e


    click_element(driver, By.CLASS_NAME, "export-citation-product")

    select_element = WebDriverWait(driver, 10).until(
                    EC.visibility_of_element_located((By.ID, "selectCitationStyle"))
                )
    
    citation = driver.find_element(By.ID, "citationText") #Need to put this after selectCitationStyle becomes visible
    initial_text = citation.text
    
    select = Select(select_element)
    select.select_by_value(citation_style.value)

    try:
        WebDriverWait(driver, 10).until(
            lambda d: citation.text != initial_text
        )
        citation = citation.text
    except Exception as e:
        print("error at waiting for citation to change")
        raise e

    driver.close()
    return abstract, citation, authors

#Get links of all articles from link
def get_links(url):
    domain = "https://www.cambridge.org"
    r = requests.get(url)
    soup = BeautifulSoup(r.content, "html.parser")

    s = soup.find('h4', class_="journal-article-listing-type")
    siblings = s.findNextSiblings()

    result = []
    for sibling in siblings:
        if sibling.name == "h4":
            break
        result.append(sibling)

    siblings = result
    links = list(map(lambda x: domain + x.find('a').get('href'), siblings))
    print("Expected number of rows (accounting for column names): ", len(links) + 1)
    return links

def parallel_get_info(link, citation_style):
    while True:
        try:
            abstract, citation, authors = get_info(link, citation_style)
            # Create a dictionary with 'Authors' as a list of authors
            return {'Chicago Citation': citation, 'Abstract': abstract,  'First Author Institution': authors[0], 'Other Author Institutions': ' / '.join(authors[1:])}
        except Exception as e:
            print(f"Error occured, retrying")

def scrape(link, max_workers=10, output_file='output', csv=False, excel=True, citation_style=CitationStyle.CHICAGO):
    """
    Input: link (str), max_workers (int), output_filename (str), csv (bool), excel (bool)
    Output:
    """
    links = get_links(link)

    # Initialize an empty DataFrame to store results
    df = pd.DataFrame()

    # Set up a ThreadPoolExecutor for parallel execution
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit tasks to the executor for each link
        future_to_link = {executor.submit(parallel_get_info, link, citation_style): link for link in links}
        
        # As each task completes, append the result to the DataFrame
        for future in as_completed(future_to_link):
            result = future.result()
            if result:  # If result is not None
                df = pd.concat([df, pd.DataFrame([result])], ignore_index=True)

    # Save the final DataFrame to an Excel file
    if(excel):
        df.to_excel(f'{output_file}.xlsx', index=False)
    if(csv):
        df.to_csv(f'{output_file}.csv', index=False)


# REPLACE LINK WITH THE LINK
# LOOK AT THE ORANGE TEXT TO SEE THE PARAMETERS, AND ADD THEM INTO THE scrape(link, csv = True) TO CHANGE OPTIONS
def main():
    # link = "https://www.cambridge.org/core/journals/american-political-science-review/issue/C8F012F00B0AC2E021E2BC2142FA6AF5?sort=canonical.position%3Aasc&pageNum=1&searchWithinIds=C8F012F00B0AC2E021E2BC2142FA6AF5&productType=JOURNAL_ARTICLE&template=cambridge-core%2Fjournal%2Farticle-listings%2Flistings-wrapper&hideArticleJournalMetaData=true&displayNasaAds=false"
    link = input("Enter link: ")
    scrape(link)
    print("Done")

if __name__ == "__main__":
    main()