
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from selenium.common.exceptions import StaleElementReferenceException
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
import time
import pandas as pd

# grab abstract, citation in chicago, unis of authors

#To click the cite button, idk but it only works when i use this
def click_element(driver, by, value):
    max_attempts = 3
    for attempt in range(max_attempts):
        try:
            # Wait for the element to be clickable
            element = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((by, value))
            )
            time.sleep(.5)
            element.click()
            # print("Element clicked successfully!")
            break  # Exit the loop if successful
        except StaleElementReferenceException:
            pass

#Get Abstract and Chicago Citation from link
def get_info(link):
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # Enable headless mode
    chrome_options.add_argument("--no-sandbox")  # For environments where sandboxing is not available
    driver = webdriver.Chrome(options=chrome_options)
    driver.get(link)
    page_source = driver.page_source
    soup = BeautifulSoup(page_source, 'html.parser')

    # print(button)
    click_element(driver, By.LINK_TEXT, "Show author details")
    s = soup.find_all('div', class_='row author')
    authors = []
    for row in s:
        authors.append(row.text.strip().split(' Affiliation: ')[1])

    click_element(driver, By.CLASS_NAME, "export-citation-product")

    select_element = WebDriverWait(driver, 5).until(
                    EC.visibility_of_element_located((By.ID, "selectCitationStyle"))
                )
    citation = driver.find_element(By.ID, "citationText")
    initial_text = citation.text

    select = Select(select_element)
    select.select_by_value("chicagob")

    WebDriverWait(driver, 5).until(
        lambda d: citation.text != initial_text
    )
    citation = citation.text

    s = soup.find('div', class_='abstract')
    abstract = s.text
    
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

    return links

def parallel_get_info(link):
    try:
        abstract, citation, authors = get_info(link)
        # Create a dictionary with 'Authors' as a list of authors
        return {'Chicago Citation': citation, 'Abstract': abstract,  'First Author Institution': authors[0], 'Other Author Institutions': ' / '.join(authors[1:])}
    except Exception as e:
        print(f"Error with {link}: {e}")
        return None

def scrape(link, max_workers=5, output_file='output', csv=False, excel=True):
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
        future_to_link = {executor.submit(parallel_get_info, link): link for link in links}
        
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

link = "https://www.cambridge.org/core/journals/american-political-science-review/issue/C8F012F00B0AC2E021E2BC2142FA6AF5?sort=canonical.position%3Aasc&pageNum=1&searchWithinIds=C8F012F00B0AC2E021E2BC2142FA6AF5&productType=JOURNAL_ARTICLE&template=cambridge-core%2Fjournal%2Farticle-listings%2Flistings-wrapper&hideArticleJournalMetaData=true&displayNasaAds=false"
scrape(link, csv=True)
