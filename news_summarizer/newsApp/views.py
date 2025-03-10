from django.shortcuts import render
import os

from dotenv import load_dotenv
from newsapi import NewsApiClient
from textblob import TextBlob
from newspaper import Article, ArticleException
from urllib.parse import urlparse, unquote
import validators
import requests

# from textblob import download_corpora

# import nltk
from nltk.text import Text
from nltk.tokenize import sent_tokenize
from nltk.corpus import stopwords


load_dotenv() #using dotenv


# # # Create your views here.
def fetch_news_articles(api_key, num_pages=5, page_size=20):
    newsApi = NewsApiClient(api_key=api_key)
    articles = []

    for page in range(1, num_pages + 1):
        headLines = newsApi.get_top_headlines(page=page, page_size=page_size)
        articles.extend(headLines.get('articles', []))

    filtered_articles = []
    for article in articles:
        title = article.get('title')
        description = article.get('description')
        image = article.get('urlToImage')
        link = article.get('url')

        if all([description, title, link, image]) and '[Removed]' not in (title, description):
            filtered_articles.append({
                'title': title,
                'description': description,
                'image': image,
                'url': link
            })

    return filtered_articles




def index(request):
    # nltk.download('punkt', quiet=True)
    # nltk.download('stopwords', quiet=True)
    # nltk.download('vader_lexicon', quiet=True)
    
    api_key = os.getenv('api_key')
    articles = fetch_news_articles(api_key)

    mylist = [(article['title'], article['description'], article['image'], article['url']) for article in articles]
    return render(request, 'main/index.html', context={"mylist": mylist})



def get_website_name(url):
    parsed_url = urlparse(url)
    domain = parsed_url.netloc
    if domain.startswith("www."):
        domain = domain[4:]
    return domain


def ArticleDetail(request):
    
    url = request.POST.get('url')
    
    if not url:
        return render(request, 'main/article.html', {'error': 'URL parameter is missing', 'url': None})

    url = unquote(url)
    if not validators.url(url):
        return render(request, 'main/article.html', {'error': 'Invalid URL', 'url': url})
    
    headers = {
        'User-Agent': 'Mozilla/5.0',  # Mimic a browser request to avoid getting blocked
    }
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
    except requests.RequestException as e:
        return render(request, 'main/article.html', {'error': f'Failed to download the content of the URL: {e}', 'url': url})
    
    try:
        article = Article(url)
        article.download()
        article.parse()
        article.nlp()
    except ArticleException as e:
        return render(request, 'main/article.html', {'error': f'Failed to process the article: {e}', 'url': url})
    
    title = article.title
    authors = ', '.join(article.authors)
    if not authors:
        authors = get_website_name(url)
    
    publish_date = article.publish_date
    if publish_date:
        publish_date = publish_date.strftime('%B %d, %Y')
    else:
        publish_date = "N/A"
    
    # article_text = article.text
    # sentences = nltk.sent_tokenize(article_text)  # Using NLTK for sentence tokenization

    sentences = sent_tokenize(article.text)
    stop_words = set(stopwords.words('english'))
    filtered_sentences = [sentence for sentence in sentences if not all(word in stop_words for word in sentence.split())]

    # Create a Text object for frequency analysis
    text = Text(filtered_sentences)
    max_summarized_sentences = 5
    summary = ' '.join(text[:max_summarized_sentences])
    
    top_image = article.top_image
    
    analysis = TextBlob(article.text)
    polarity = analysis.sentiment.polarity
    
    if polarity > 0:
        sentiment = 'happy 😊'
    elif polarity < 0:
        sentiment = 'sad 😟'
    else:
        sentiment = 'neutral 😐'
    
    context = {
        'title': title,
        'authors': authors,
        'publish_date': publish_date,
        'summary': summary,
        'top_image': top_image,
        'sentiment': sentiment,
        'url': url
    }
    return render(request, 'main/article.html', context)




def search_news(request):
    query = request.GET.get('query')
    articles = []

    if query:
        url = f'https://newsapi.org/v2/everything?q={query}&apiKey={os.getenv("api_key")}'
        response = requests.get(url)
        data = response.json()

        if response.status_code == 200:
            raw_articles = data.get('articles', [])
            # Filter out articles with missing essential information
            articles = [
                article for article in raw_articles
                if article.get('title') and article.get('description') and article.get('url') and article.get('urlToImage')
            ]
        else:
            error_message = data.get('message', 'An error occurred while fetching the news.')
            return render(request, 'main/search_results.html', {'error': error_message})
    
    else:
        return render(request, 'main/search_results.html', {'error': 'No search query provided.'})
    
    return render(request, 'main/search_results.html', {'articles': articles})






def about(request):
    return render(request, 'main/about.html')