# -*- coding: utf-8 -*-
import re
import scrapy
from bs4 import BeautifulSoup
from scrapy.http import Request

# TODO: Please provide values for the following variables
# Domains only, no urls
ALLOWED_DOMAINS = ['incognito.forumperso.com']
# Starting urls
START_URLS = ['https://incognito.forumperso.com']
# Is login required? True or False.
FORM_LOGIN = False
# Login username
USERNAME = ''
# Login password
PASSWORD = ''
# Login url
LOGIN_URL = ''


class PhpbbSpider(scrapy.Spider):
    
    name = 'phpBB'
    allowed_domains = ALLOWED_DOMAINS
    start_urls = START_URLS
    form_login = FORM_LOGIN
    if form_login is True:
        username = USERNAME
        password = PASSWORD
        login_url = LOGIN_URL
        start_urls.insert(0, login_url)

    def parse(self, response):
        # LOGIN TO PHPBB BOARD AND CALL AFTER_LOGIN
        if self.form_login:
            formxpath = '//*[contains(@action, "login")]'
            formdata = {'username': self.username, 'password': self.password}
            form_request = scrapy.FormRequest.from_response(
                    response,
                    formdata=formdata,
                    formxpath=formxpath,
                    callback=self.after_login,
                    dont_click=False
            )
            yield form_request
        else:
            # REQUEST SUB-FORUM TITLE LINKS
            links = response.xpath('//a[@class="forumtitle"]/@href').extract()
            for link in links:
                yield scrapy.Request(response.urljoin(link), callback=self.parse_topics)

    def after_login(self, response):
        # CHECK LOGIN SUCCESS BEFORE MAKING REQUESTS
        if b'authentication failed' in response.body:
            self.logger.error('Login failed.')
            return
        else:
            # REQUEST SUB-FORUM TITLE LINKS
            links = response.xpath('//a[@class="forumtitle"]/@href').extract()
            for link in links:
                yield scrapy.Request(response.urljoin(link), callback=self.parse_topics)

    def parse_topics(self, response):
        # REQUEST TOPIC TITLE LINKS
        links = response.xpath('//a[@class="topictitle"]/@href').extract()
        for link in links:
            yield scrapy.Request(response.urljoin(link), callback=self.parse_posts)
        
        # IF NEXT PAGE EXISTS, FOLLOW
        next_link = response.xpath('//li[@class="next"]//a[@rel="next"]/@href').extract_first()
        if next_link:
            yield scrapy.Request(response.urljoin(next_link), callback=self.parse_topics)
      
    def parse_posts(self, response):
        # COLLECT FORUM POST DATA
        page_title = response.css('h1 a::text').get().strip()
        pathname = ' '.join(p.strip() for p in response.css('.pathname-box *::text').getall())
        posts = []
        for post in response.css('.post'):
            postprofile = post.css('.postprofile')
            username = postprofile.css('dt strong::text').get()
            if not username:  # "Sujets similaires"
                continue
            if username == 'Contenu sponsorisé':
                continue
            user_role = postprofile.css('dd:nth-child(2)::text').get().strip()
            post_count = postprofile.css('dd:nth-child(4)::text').get().strip()
            post_time = post.css('.author::text').get().split(' le ')[1].strip()
            post_text = post.css('.content').get().strip()
            posts.append({
                'Username': username,
                'UserRole': user_role,
                'PostCount': post_count,
                'PostTime': post_time,
                'PostText': post_text,
            })
        yield {
            'title': page_title,
            'pathname': pathname,
            'posts': posts,
        }
        
        # CLICK THROUGH NEXT PAGE
        # Lucas: Non nécessaire pour incognito.forumperso.com
        # donc désactivé comme ces sélecteurs sont très propablement incorrects avec la version de phpBB du forum
        # next_link = response.xpath('//li[@class="next"]//a[@rel="next"]/@href').extract_first()
        # if next_link:
            # yield scrapy.Request(response.urljoin(next_link), callback=self.parse_posts)
