import os
import re
import time
import random
import requests
from flask import Flask, request, jsonify, render_template
from werkzeug.utils import secure_filename
from PyPDF2 import PdfReader
from bs4 import BeautifulSoup
from flask_cors import CORS
from urllib.parse import urljoin, quote_plus
import logging
from collections import Counter
import json

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16MB max file size

# Comprehensive skills database - extracted from resume content
PROGRAMMING_LANGUAGES = [
    "Python", "Java", "JavaScript", "TypeScript", "C++", "C#", "C", "PHP", "Ruby", "Go", 
    "Rust", "Swift", "Kotlin", "Scala", "R", "MATLAB", "Perl", "Shell", "Bash", "PowerShell",
    "Objective-C", "Dart", "Lua", "Assembly", "COBOL", "Fortran", "Haskell", "Clojure", "Elixir"
]

WEB_TECHNOLOGIES = [
    "HTML", "CSS", "React", "Angular", "Vue.js", "Node.js", "Express.js", "Django", "Flask",
    "FastAPI", "Spring Boot", "Laravel", "ASP.NET", "Bootstrap", "Tailwind CSS", "jQuery",
    "AJAX", "REST API", "GraphQL", "JSON", "XML", "WebSocket", "Next.js", "Nuxt.js", "Svelte",
    "Webpack", "Babel", "Sass", "SCSS", "Less", "Material-UI", "Ant Design", "Chakra UI"
]

DATABASES = [
    "SQL", "MySQL", "PostgreSQL", "MongoDB", "Redis", "Cassandra", "Oracle", "SQLite",
    "Firebase", "DynamoDB", "Neo4j", "Elasticsearch", "MariaDB", "CouchDB", "InfluxDB",
    "Apache Spark", "Hadoop", "BigQuery", "Snowflake", "Clickhouse", "Amazon RDS"
]

DATA_SCIENCE_AI = [
    "Machine Learning", "Deep Learning", "Data Analysis", "Data Science", "NLP", "Computer Vision",
    "TensorFlow", "PyTorch", "Scikit-learn", "Pandas", "NumPy", "Matplotlib", "Seaborn", "Jupyter",
    "Tableau", "Power BI", "Statistics", "Data Mining", "Neural Networks", "CNN", "RNN", "LSTM",
    "OpenCV", "NLTK", "spaCy", "Keras", "XGBoost", "Random Forest", "SVM", "Regression", "Classification"
]

CLOUD_DEVOPS = [
    "AWS", "Azure", "Google Cloud", "Docker", "Kubernetes", "Jenkins", "Git", "GitLab", "GitHub",
    "CI/CD", "Terraform", "Ansible", "Linux", "Ubuntu", "CentOS", "DevOps", "Microservices",
    "Serverless", "CloudFormation", "Helm", "Istio", "Prometheus", "Grafana", "ELK Stack", "Nagios"
]

MOBILE_TECHNOLOGIES = [
    "Android", "iOS", "React Native", "Flutter", "Xamarin", "Ionic", "Swift", "Objective-C",
    "Kotlin", "Java", "Mobile Development", "Cross-platform", "Native Development", "Cordova"
]

OTHER_SKILLS = [
    "Testing", "Unit Testing", "Selenium", "Postman", "Jest", "Cypress", "JUnit", "TestNG",
    "API Testing", "Automation Testing", "Manual Testing", "QA", "Figma", "Adobe XD", "Sketch",
    "UI/UX Design", "Photoshop", "Illustrator", "Agile", "Scrum", "Kanban", "JIRA", "Confluence",
    "Project Management", "Version Control", "Problem Solving", "Team Leadership", "Communication"
]

# Combine all skills
ALL_SKILLS = (PROGRAMMING_LANGUAGES + WEB_TECHNOLOGIES + DATABASES + 
              DATA_SCIENCE_AI + CLOUD_DEVOPS + MOBILE_TECHNOLOGIES + OTHER_SKILLS)

# User agents to rotate
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
]

def get_random_headers():
    """Get random headers to avoid bot detection"""
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9,hi;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache"
    }

def safe_request(url, max_retries=3):
    """Make safe HTTP requests with proper error handling"""
    for attempt in range(max_retries):
        try:
            headers = get_random_headers()
            response = requests.get(
                url, 
                headers=headers, 
                timeout=20, 
                allow_redirects=True,
                verify=True
            )
            
            if response.status_code == 200:
                return response
            elif response.status_code == 429:
                wait_time = random.uniform(3, 8) * (attempt + 1)
                logger.warning(f"Rate limited, waiting {wait_time:.1f}s")
                time.sleep(wait_time)
            else:
                logger.warning(f"HTTP {response.status_code} for {url}")
                
        except requests.exceptions.RequestException as e:
            logger.warning(f"Request failed (attempt {attempt + 1}): {str(e)}")
            if attempt < max_retries - 1:
                time.sleep(random.uniform(2, 5))
    
    return None

# -----------------------------
# Enhanced Skills Extraction from Resume
# -----------------------------
def extract_skills_from_resume(file_path):
    """Extract technical skills directly from resume PDF content"""
    logger.info("Starting skill extraction from resume...")
    
    # Extract text from PDF
    text = ""
    try:
        pdf_reader = PdfReader(file_path)
        for page_num, page in enumerate(pdf_reader.pages):
            try:
                extracted = page.extract_text()
                if extracted:
                    text += extracted + "\n"
            except Exception as e:
                logger.warning(f"Error extracting page {page_num}: {e}")
                continue
    except Exception as e:
        logger.error(f"Error reading PDF: {e}")
        return []
    
    if not text.strip():
        logger.error("No text extracted from PDF")
        return []
    
    logger.info(f"Extracted {len(text)} characters from resume")
    
    # Clean and normalize text
    text = re.sub(r'\s+', ' ', text.strip())
    text_lower = text.lower()
    
    # Find skills with multiple matching patterns
    found_skills = []
    skill_matches = {}
    
    for skill in ALL_SKILLS:
        skill_lower = skill.lower()
        match_count = 0
        
        # Pattern 1: Exact word boundary match (highest priority)
        exact_pattern = rf'\b{re.escape(skill_lower)}\b'
        exact_matches = len(re.findall(exact_pattern, text_lower))
        if exact_matches > 0:
            match_count += exact_matches * 3  # Higher weight for exact matches
        
        # Pattern 2: Case-insensitive substring match
        if skill_lower in text_lower:
            match_count += 1
        
        # Pattern 3: Handle variations (e.g., "Node.js" vs "NodeJS")
        variations = []
        if '.' in skill_lower:
            variations.append(skill_lower.replace('.', ''))
        if ' ' in skill_lower:
            variations.append(skill_lower.replace(' ', ''))
        if '-' in skill_lower:
            variations.append(skill_lower.replace('-', ''))
        
        for variation in variations:
            if variation in text_lower:
                match_count += 1
        
        # Pattern 4: Common abbreviations
        abbreviations = {
            'javascript': ['js'],
            'typescript': ['ts'],
            'machine learning': ['ml'],
            'artificial intelligence': ['ai'],
            'user interface': ['ui'],
            'user experience': ['ux'],
            'application programming interface': ['api'],
            'structured query language': ['sql'],
        }
        
        for full_name, abbrevs in abbreviations.items():
            if skill_lower == full_name:
                for abbrev in abbrevs:
                    if f'\\b{abbrev}\\b' in text_lower:
                        match_count += 2
        
        # Store skills with sufficient matches
        if match_count >= 2:  # Minimum threshold
            found_skills.append(skill)
            skill_matches[skill] = match_count
    
    # Remove duplicates and sort by match frequency
    unique_skills = list(set(found_skills))
    unique_skills.sort(key=lambda x: skill_matches.get(x, 0), reverse=True)
    
    logger.info(f"Found {len(unique_skills)} skills: {unique_skills[:10]}...")
    return unique_skills

# -----------------------------
# Job Role Matching
# -----------------------------
def match_job_roles(skills):
    """Match skills to relevant job roles"""
    if not skills:
        return []
    
    skills_set = set(skill.lower() for skill in skills)
    
    # Define job roles with required and preferred skills
    job_roles = {
        "Python Developer": {
            "required": ["python"],
            "preferred": ["django", "flask", "fastapi", "sql", "git", "rest api"],
            "weight": 1.4
        },
        "Full Stack Developer": {
            "required": ["javascript", "html", "css"],
            "preferred": ["react", "node.js", "python", "sql", "git", "mongodb"],
            "weight": 1.3
        },
        "Data Scientist": {
            "required": ["python", "data analysis"],
            "preferred": ["machine learning", "pandas", "numpy", "sql", "statistics", "matplotlib"],
            "weight": 1.6
        },
        "Frontend Developer": {
            "required": ["javascript", "html", "css"],
            "preferred": ["react", "angular", "vue.js", "typescript", "bootstrap"],
            "weight": 1.2
        },
        "Backend Developer": {
            "required": ["python", "java", "node.js"],
            "preferred": ["sql", "mongodb", "rest api", "microservices", "docker"],
            "weight": 1.4
        },
        "Machine Learning Engineer": {
            "required": ["python", "machine learning"],
            "preferred": ["tensorflow", "pytorch", "deep learning", "nlp", "aws"],
            "weight": 1.7
        },
        "DevOps Engineer": {
            "required": ["linux", "docker"],
            "preferred": ["kubernetes", "aws", "jenkins", "terraform", "ci/cd"],
            "weight": 1.5
        },
        "Mobile Developer": {
            "required": ["android", "ios", "react native", "flutter"],
            "preferred": ["java", "swift", "kotlin", "mobile development"],
            "weight": 1.3
        },
        "Database Administrator": {
            "required": ["sql", "mysql", "postgresql"],
            "preferred": ["oracle", "mongodb", "database design", "performance tuning"],
            "weight": 1.3
        },
        "UI/UX Designer": {
            "required": ["figma", "ui/ux design"],
            "preferred": ["adobe xd", "sketch", "photoshop", "wireframing", "prototyping"],
            "weight": 1.2
        }
    }
    
    matches = []
    
    for role_name, role_data in job_roles.items():
        required_skills = [s.lower() for s in role_data["required"]]
        preferred_skills = [s.lower() for s in role_data["preferred"]]
        
        # Calculate skill matches
        required_matches = len(skills_set & set(required_skills))
        preferred_matches = len(skills_set & set(preferred_skills))
        
        # Must have at least one required skill
        if required_matches == 0:
            continue
        
        # Calculate score
        required_score = (required_matches / len(required_skills)) * 70
        preferred_score = (preferred_matches / len(preferred_skills)) * 30
        
        total_score = (required_score + preferred_score) * role_data["weight"]
        final_score = min(total_score, 100)
        
        matches.append({
            "title": role_name,
            "score": round(final_score, 1),
            "required_matches": required_matches,
            "total_required": len(required_skills),
            "preferred_matches": preferred_matches,
            "total_preferred": len(preferred_skills)
        })
    
    # Sort by score
    matches.sort(key=lambda x: x["score"], reverse=True)
    return matches[:6]

# -----------------------------
# Enhanced Job Scraping with Better Company Extraction
# -----------------------------
def scrape_internshala_jobs(skills, limit=6):
    """Scrape Internshala jobs based on extracted skills"""
    jobs = []
    
    if not skills:
        return jobs
    
    # Create targeted search queries from skills
    search_queries = []
    for skill in skills[:3]:  # Top 3 skills
        queries = [
            f"{skill} developer",
            f"{skill} engineer", 
            f"{skill} intern",
            skill.lower()
        ]
        search_queries.extend(queries)
    
    # Remove duplicates and limit queries
    search_queries = list(set(search_queries))[:4]
    
    for query in search_queries:
        try:
            # Format query for URL
            formatted_query = query.replace(" ", "-").lower()
            
            # Try different URL patterns
            urls = [
                f"https://internshala.com/internships/keywords-{formatted_query}",
                f"https://internshala.com/jobs/keywords-{formatted_query}",
                f"https://internshala.com/internships/{formatted_query}"
            ]
            
            for url in urls:
                logger.info(f"Scraping Internshala: {query}")
                response = safe_request(url)
                
                if not response:
                    continue
                
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Try multiple selectors for job cards
                job_cards = []
                selectors = [
                    'div.individual_internship',
                    'div.internship_meta',
                    'div[id*="internship"]',
                    'div.job-tile',
                    'div.container-fluid.individual_internship'
                ]
                
                for selector in selectors:
                    job_cards = soup.select(selector)[:limit]
                    if job_cards:
                        logger.info(f"Found {len(job_cards)} job cards with selector: {selector}")
                        break
                
                for card in job_cards:
                    try:
                        # Extract title with multiple selectors
                        title = None
                        title_selectors = [
                            'h3.job-internship-name a',
                            'h4.job-internship-name a',
                            'h3 a',
                            '.profile h3 a',
                            '.heading_4_5 a',
                            'a[href*="internship/detail"]'
                        ]
                        
                        for sel in title_selectors:
                            elem = card.select_one(sel)
                            if elem:
                                title = elem.get_text(strip=True)
                                break
                        
                        if not title:
                            # Try without anchor tag
                            title_elem = card.select_one('h3, h4, .profile, .heading_4_5')
                            if title_elem:
                                title = title_elem.get_text(strip=True)
                        
                        # Extract company with multiple selectors
                        company = None
                        company_selectors = [
                            '.company-name',
                            '.company_name',
                            'p.company_name',
                            'a.link_display_like_text',
                            '.company',
                            'h4 + p',
                            '.text-muted'
                        ]
                        
                        for sel in company_selectors:
                            elem = card.select_one(sel)
                            if elem:
                                company_text = elem.get_text(strip=True)
                                # Clean up company name
                                company_text = re.sub(r'\s+', ' ', company_text)
                                if company_text and len(company_text) < 100:  # Reasonable company name length
                                    company = company_text
                                    break
                        
                        # Extract link
                        link = None
                        link_selectors = [
                            'a[href*="internship/detail"]',
                            'a[href*="job/detail"]',
                            '.view_detail_button',
                            'h3 a',
                            'h4 a'
                        ]
                        
                        for sel in link_selectors:
                            elem = card.select_one(sel)
                            if elem and elem.get('href'):
                                href = elem['href']
                                if href.startswith('/'):
                                    link = f"https://internshala.com{href}"
                                elif href.startswith('http'):
                                    link = href
                                break
                        
                        # Validate and add job
                        if title and len(title) > 5:  # Basic validation
                            jobs.append({
                                "title": title,
                                "company": company or "Internshala Partner Company",
                                "link": link or f"https://internshala.com/internships/keywords-{formatted_query}",
                                "source": "Internshala",
                                "query_used": query
                            })
                            
                    except Exception as e:
                        logger.error(f"Error parsing Internshala job card: {e}")
                        continue
                
                if jobs:
                    break
                    
                time.sleep(random.uniform(1, 3))
            
            if len(jobs) >= limit:
                break
                
        except Exception as e:
            logger.error(f"Error scraping Internshala for '{query}': {e}")
            continue
    
    return jobs[:limit]

def scrape_naukri_jobs(skills, limit=6):
    """Scrape Naukri jobs based on extracted skills"""
    jobs = []
    
    if not skills:
        return jobs
    
    # Create search queries from skills
    search_queries = [f"{skill} jobs" for skill in skills[:3]]
    
    for query in search_queries:
        try:
            # Format query for Naukri URL
            formatted_query = query.replace(" ", "-").lower()
            url = f"https://www.naukri.com/{formatted_query}"
            
            logger.info(f"Scraping Naukri: {query}")
            response = safe_request(url)
            
            if response:
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Try multiple selectors
                job_cards = []
                selectors = [
                    'article.jobTuple',
                    'div.srp-jobtuple-wrapper',
                    'div.jobTuple',
                    'div[class*="job"]'
                ]
                
                for selector in selectors:
                    job_cards = soup.select(selector)[:limit]
                    if job_cards:
                        logger.info(f"Found {len(job_cards)} Naukri jobs")
                        break
                
                for card in job_cards:
                    try:
                        # Extract title
                        title = None
                        title_selectors = [
                            'a.title',
                            '.jobTupleHeader .title a',
                            'h3 a',
                            'h4 a',
                            '[data-job-title]'
                        ]
                        
                        for sel in title_selectors:
                            elem = card.select_one(sel)
                            if elem:
                                title = elem.get_text(strip=True)
                                break
                        
                        # Extract company
                        company = None
                        company_selectors = [
                            'a.subTitle',
                            '.company',
                            '.companyInfo',
                            '.comp-name',
                            '.jobTupleHeader .subTitle'
                        ]
                        
                        for sel in company_selectors:
                            elem = card.select_one(sel)
                            if elem:
                                company = elem.get_text(strip=True)
                                if company and len(company) < 80:
                                    break
                        
                        # Extract link
                        link = None
                        link_elem = card.select_one('a.title, h3 a, h4 a')
                        if link_elem and link_elem.get('href'):
                            href = link_elem['href']
                            if href.startswith('/'):
                                link = f"https://www.naukri.com{href}"
                            elif href.startswith('http'):
                                link = href
                        
                        if title:
                            jobs.append({
                                "title": title,
                                "company": company or "Naukri Partner Company",
                                "link": link or f"https://www.naukri.com/{formatted_query}",
                                "source": "Naukri",
                                "query_used": query
                            })
                            
                    except Exception as e:
                        logger.error(f"Error parsing Naukri job: {e}")
                        continue
            
            time.sleep(random.uniform(1, 3))
            
            if len(jobs) >= limit:
                break
                
        except Exception as e:
            logger.error(f"Error scraping Naukri for '{query}': {e}")
    
    return jobs[:limit]

def scrape_indeed_jobs(skills, limit=6):
    """Scrape Indeed jobs based on extracted skills"""
    jobs = []
    
    if not skills:
        return jobs
    
    search_queries = [f"{skill} developer" for skill in skills[:3]]
    
    for query in search_queries:
        try:
            encoded_query = quote_plus(query)
            url = f"https://in.indeed.com/jobs?q={encoded_query}&l=India"
            
            logger.info(f"Scraping Indeed: {query}")
            response = safe_request(url)
            
            if response:
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Try multiple selectors
                job_cards = []
                selectors = [
                    'div[data-result-id]',
                    'div.job_seen_beacon',
                    'td.resultContent',
                    'div.slider_container'
                ]
                
                for selector in selectors:
                    job_cards = soup.select(selector)[:limit]
                    if job_cards:
                        logger.info(f"Found {len(job_cards)} Indeed jobs")
                        break
                
                for card in job_cards:
                    try:
                        # Extract title
                        title = None
                        title_selectors = [
                            'h2 a span[title]',
                            'h2.jobTitle a span',
                            '.jobTitle a',
                            'h2 span[title]'
                        ]
                        
                        for sel in title_selectors:
                            elem = card.select_one(sel)
                            if elem:
                                title = elem.get('title') or elem.get_text(strip=True)
                                break
                        
                        # Extract company
                        company = None
                        company_selectors = [
                            'span.companyName',
                            '.companyName',
                            'span[data-testid="company-name"]',
                            '.company'
                        ]
                        
                        for sel in company_selectors:
                            elem = card.select_one(sel)
                            if elem:
                                company = elem.get_text(strip=True)
                                break
                        
                        # Extract link
                        link = None
                        link_elem = card.select_one('h2 a, .jobTitle a')
                        if link_elem and link_elem.get('href'):
                            href = link_elem['href']
                            if href.startswith('/'):
                                link = f"https://in.indeed.com{href}"
                            elif href.startswith('http'):
                                link = href
                        
                        if title:
                            jobs.append({
                                "title": title,
                                "company": company or "Indeed Partner Company",
                                "link": link or f"https://in.indeed.com/jobs?q={encoded_query}&l=India",
                                "source": "Indeed",
                                "query_used": query
                            })
                            
                    except Exception as e:
                        logger.error(f"Error parsing Indeed job: {e}")
                        continue
            
            time.sleep(random.uniform(1, 3))
            
            if len(jobs) >= limit:
                break
                
        except Exception as e:
            logger.error(f"Error scraping Indeed for '{query}': {e}")
    
    return jobs[:limit]

def scrape_all_jobs(skills):
    """Scrape jobs from all portals based on extracted skills"""
    logger.info(f"Starting job scraping for skills: {skills[:5]}...")
    
    all_jobs = []
    
    # Scrape from each portal
    scrapers = [
        ("Internshala", scrape_internshala_jobs),
        ("Naukri", scrape_naukri_jobs),
        ("Indeed", scrape_indeed_jobs)
    ]
    
    for scraper_name, scraper_func in scrapers:
        try:
            logger.info(f"Scraping {scraper_name}...")
            jobs = scraper_func(skills, 6)  # Get 6 jobs from each portal
            all_jobs.extend(jobs)
            logger.info(f"{scraper_name}: Found {len(jobs)} jobs")
            
            # Delay between scrapers
            time.sleep(random.uniform(2, 4))
            
        except Exception as e:
            logger.error(f"Error in {scraper_name} scraper: {e}")
    
    # Remove duplicates based on title and company
    seen_jobs = set()
    unique_jobs = []
    
    for job in all_jobs:
        job_key = (job['title'].lower().strip(), job['company'].lower().strip())
        if job_key not in seen_jobs:
            seen_jobs.add(job_key)
            unique_jobs.append(job)
    
    logger.info(f"Total unique jobs found: {len(unique_jobs)}")
    return unique_jobs[:15]  # Return top 15 jobs

# -----------------------------
# Flask Routes
# -----------------------------
@app.route("/")
def home():
    """Render the main application page"""
    return render_template("index.html")

@app.route("/upload", methods=["POST"])
def upload_resume():
    """Handle resume upload and job matching"""
    try:
        # Validate file upload
        if "resume" not in request.files:
            return jsonify({"error": "No file uploaded"}), 400
        
        file = request.files["resume"]
        if file.filename == "":
            return jsonify({"error": "No file selected"}), 400
        
        if not file.filename.lower().endswith('.pdf'):
            return jsonify({"error": "Only PDF files are supported"}), 400
        
        # Save the uploaded file
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        file.save(file_path)
        
        logger.info(f"Processing resume: {filename}")
        
        # Extract skills from the resume
        logger.info("Extracting skills from resume PDF...")
        skills = extract_skills_from_resume(file_path)
        
        if not skills:
            # Clean up file
            try:
                os.remove(file_path)
            except:
                pass
            return jsonify({
                "error": "No technical skills found in your resume",
                "suggestion": "Make sure your resume includes technical skills like programming languages (Python, Java), frameworks (React, Django), databases (SQL, MongoDB), or tools (Git, Docker). Use standard skill names and include a 'Skills' or 'Technical Skills' section."
            }), 400
        
        logger.info(f"Extracted {len(skills)} skills from resume")
        
        # Match job roles based on extracted skills
        logger.info("Matching job roles...")
        role_matches = match_job_roles(skills)
        
        # Scrape job opportunities based on extracted skills
        logger.info("Scraping job opportunities based on your skills...")
        job_opportunities = scrape_all_jobs(skills)
        
        # Clean up the uploaded file
        try:
            os.remove(file_path)
        except:
            pass
        
        # Prepare response
        response_data = {
            "success": True,
            "skills": skills[:25],  # Show up to 25 skills
            "skills_count": len(skills),
            "role_matches": role_matches,
            "job_listings": job_opportunities,
            "jobs_count": len(job_opportunities),
            "message": f"Successfully analyzed your resume! Found {len(skills)} technical skills and {len(job_opportunities)} relevant job opportunities.",
            "top_skills": skills[:10],  # Top 10 skills for summary
            "processing_info": {
                "total_skills_detected": len(skills),
                "job_roles_matched": len(role_matches),
                "portals_searched": ["Internshala", "Naukri", "Indeed"],
                "search_queries_used": len(set([skill.lower() for skill in skills[:3]]))
            }
        }
        
        logger.info(f"Successfully processed resume - {len(skills)} skills, {len(job_opportunities)} jobs")
        return jsonify(response_data)
        
    except Exception as e:
        # Clean up file on error
        try:
            if 'file_path' in locals():
                os.remove(file_path)
        except:
            pass
        
        logger.error(f"Error processing resume: {str(e)}")
        return jsonify({
            "error": "An error occurred while processing your resume",
            "details": str(e) if app.debug else "Please try again with a different PDF file"
        }), 500

@app.route("/api/skills", methods=["GET"])
def get_available_skills():
    """Return all available skills in the database"""
    skills_by_category = {
        "Programming Languages": PROGRAMMING_LANGUAGES,
        "Web Technologies": WEB_TECHNOLOGIES,
        "Databases": DATABASES,
        "Data Science & AI": DATA_SCIENCE_AI,
        "Cloud & DevOps": CLOUD_DEVOPS,
        "Mobile Technologies": MOBILE_TECHNOLOGIES,
        "Other Skills": OTHER_SKILLS
    }
    
    return jsonify({
        "success": True,
        "skills_by_category": skills_by_category,
        "total_skills": len(ALL_SKILLS)
    })

@app.route("/api/analyze", methods=["POST"])
def analyze_skills():
    """Analyze provided skills and return job matches"""
    try:
        data = request.get_json()
        if not data or 'skills' not in data:
            return jsonify({"error": "No skills provided"}), 400
        
        skills = data['skills']
        if not isinstance(skills, list) or not skills:
            return jsonify({"error": "Skills must be a non-empty list"}), 400
        
        # Validate skills
        valid_skills = [skill for skill in skills if skill in ALL_SKILLS]
        if not valid_skills:
            return jsonify({"error": "No valid skills provided"}), 400
        
        # Match job roles
        role_matches = match_job_roles(valid_skills)
        
        # Optionally scrape jobs (can be disabled for API usage)
        include_jobs = data.get('include_jobs', False)
        job_opportunities = []
        
        if include_jobs:
            job_opportunities = scrape_all_jobs(valid_skills)
        
        response_data = {
            "success": True,
            "skills": valid_skills,
            "skills_count": len(valid_skills),
            "role_matches": role_matches,
            "job_listings": job_opportunities,
            "jobs_count": len(job_opportunities)
        }
        
        return jsonify(response_data)
        
    except Exception as e:
        logger.error(f"Error in analyze_skills: {str(e)}")
        return jsonify({
            "error": "An error occurred during analysis",
            "details": str(e) if app.debug else "Please try again"
        }), 500

@app.route("/api/health", methods=["GET"])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "version": "1.0.0",
        "skills_loaded": len(ALL_SKILLS),
        "upload_folder": app.config["UPLOAD_FOLDER"]
    })

@app.errorhandler(413)
def too_large(e):
    return jsonify({
        "error": "File too large",
        "message": "Please upload a PDF file smaller than 16MB"
    }), 413

@app.errorhandler(404)
def not_found(e):
    return jsonify({
        "error": "Endpoint not found",
        "message": "Please check the API documentation"
    }), 404

@app.errorhandler(500)
def internal_error(e):
    return jsonify({
        "error": "Internal server error",
        "message": "Something went wrong on our end"
    }), 500

# -----------------------------
# Additional Utility Functions
# -----------------------------
def generate_skills_report(skills, role_matches):
    """Generate a detailed skills analysis report"""
    if not skills:
        return {}
    
    # Categorize skills
    categorized_skills = {
        "Programming Languages": [],
        "Web Technologies": [],
        "Databases": [],
        "Data Science & AI": [],
        "Cloud & DevOps": [],
        "Mobile Technologies": [],
        "Other Skills": []
    }
    
    skill_categories = {
        "Programming Languages": PROGRAMMING_LANGUAGES,
        "Web Technologies": WEB_TECHNOLOGIES,
        "Databases": DATABASES,
        "Data Science & AI": DATA_SCIENCE_AI,
        "Cloud & DevOps": CLOUD_DEVOPS,
        "Mobile Technologies": MOBILE_TECHNOLOGIES,
        "Other Skills": OTHER_SKILLS
    }
    
    for skill in skills:
        for category, category_skills in skill_categories.items():
            if skill in category_skills:
                categorized_skills[category].append(skill)
                break
    
    # Calculate category strengths
    category_strengths = {}
    for category, category_skills in categorized_skills.items():
        if category_skills:
            total_possible = len(skill_categories[category])
            strength_score = (len(category_skills) / total_possible) * 100
            category_strengths[category] = {
                "skills": category_skills,
                "count": len(category_skills),
                "total_possible": total_possible,
                "strength_percentage": round(strength_score, 1)
            }
    
    return {
        "categorized_skills": categorized_skills,
        "category_strengths": category_strengths,
        "top_categories": sorted(
            category_strengths.items(),
            key=lambda x: x[1]["strength_percentage"],
            reverse=True
        )[:3],
        "skills_summary": {
            "total_skills": len(skills),
            "unique_categories": len([cat for cat, skills_list in categorized_skills.items() if skills_list]),
            "top_skill_category": max(categorized_skills.items(), key=lambda x: len(x[1]))[0] if skills else None
        }
    }

@app.route("/api/report", methods=["POST"])
def generate_report():
    """Generate detailed skills and career analysis report"""
    try:
        data = request.get_json()
        if not data or 'skills' not in data:
            return jsonify({"error": "No skills provided"}), 400
        
        skills = data['skills']
        role_matches = match_job_roles(skills)
        skills_report = generate_skills_report(skills, role_matches)
        
        # Generate career recommendations
        recommendations = []
        if role_matches:
            top_role = role_matches[0]
            recommendations.append({
                "type": "career_focus",
                "title": f"Focus on {top_role['title']} Skills",
                "description": f"You have a {top_role['score']}% match for {top_role['title']} roles. Consider strengthening related skills.",
                "priority": "high"
            })
        
        # Skill gap analysis
        all_skills_set = set(ALL_SKILLS)
        user_skills_set = set(skills)
        missing_skills = all_skills_set - user_skills_set
        
        # Suggest top missing skills for the best-matched role
        skill_suggestions = []
        if role_matches and missing_skills:
            top_role = role_matches[0]['title']
            # This is a simplified suggestion - in a real app, you'd have more sophisticated logic
            common_missing = list(missing_skills)[:10]  # Top 10 missing skills
            skill_suggestions = common_missing
        
        report = {
            "success": True,
            "skills_analysis": skills_report,
            "role_matches": role_matches,
            "recommendations": recommendations,
            "skill_suggestions": skill_suggestions,
            "report_metadata": {
                "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                "analysis_version": "1.0.0",
                "total_skills_analyzed": len(skills)
            }
        }
        
        return jsonify(report)
        
    except Exception as e:
        logger.error(f"Error generating report: {str(e)}")
        return jsonify({
            "error": "Failed to generate report",
            "details": str(e) if app.debug else "Please try again"
        }), 500

# -----------------------------
# Colab-specific setup and run function
# -----------------------------
def run_colab_app():
    """Function to run the Flask app in Google Colab"""
    # Ensure upload directory exists
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    
    # Set up basic logging
    logging.basicConfig(level=logging.INFO)
    logger.info("Starting Resume Job Matcher for Google Colab")
    logger.info(f"Skills database loaded: {len(ALL_SKILLS)} skills")
    
    # Run in a separate thread to avoid blocking Colab
    def run_app():
        app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)
    
    thread = threading.Thread(target=run_app)
    thread.daemon = True
    thread.start()
    
    # Import and set up ngrok for public URL (if available)
    try:
        from pyngrok import ngrok
        
        # Kill any existing tunnels
        ngrok.kill()
        
        # Create new tunnel
        public_url = ngrok.connect(5000)
        print(f"\n🚀 Resume Job Matcher is now running!")
        print(f"📱 Access your app at: {public_url}")
        print(f"📝 Upload a PDF resume to get started!")
        print(f"\n⚡ Features:")
        print(f"  • Extract {len(ALL_SKILLS)} different technical skills")
        print(f"  • Match to {len(job_roles)} job roles")
        print(f"  • Search jobs on Internshala, Naukri, Indeed")
        print(f"\n🔗 Click the link above to open the app!")
        
        return public_url
        
    except ImportError:
        # If ngrok is not available, use localhost
        print(f"\n🚀 Resume Job Matcher is running on http://localhost:5000")
        print(f"📝 Upload a PDF resume to get started!")
        print(f"\n💡 Install pyngrok for public URL: !pip install pyngrok")
        return "http://localhost:5000"

# Auto-install pyngrok if in Colab environment
def setup_colab():
    """Set up the environment for Google Colab"""
    try:
        import google.colab
        # We're in Colab, install pyngrok
        print("📦 Installing pyngrok for public URL access...")
        os.system("pip install pyngrok > /dev/null 2>&1")
        print("✅ Setup complete!")
        return True
    except ImportError:
        return False

# Main execution for different environments
if __name__ == "__main__":
    is_colab = setup_colab()
    
    if is_colab:
        # Running in Google Colab
        public_url = run_colab_app()
    else:
        # Running locally
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)
        port = int(os.environ.get("PORT", 5000))
        debug_mode = os.environ.get("FLASK_DEBUG", "False").lower() == "true"
        
        logger.info(f"Starting Resume Job Matcher application on port {port}")
        logger.info(f"Debug mode: {debug_mode}")
        logger.info(f"Skills database loaded: {len(ALL_SKILLS)} skills")
        
        app.run(
            host="0.0.0.0",
            port=port,
            debug=debug_mode,
            threaded=True
        )
    
    app.run(
        host="0.0.0.0",
        port=port,
        debug=debug_mode,
        threaded=True
    )