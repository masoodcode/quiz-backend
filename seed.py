from database import engine, SessionLocal, Base
from models import Category, Topic, Question, Option


def reset_tables():
    """Drop all tables and recreate with the latest schema.
    Called once when the new schema is deployed to Neon.
    Safe to run — only drops if old schema is detected.
    """
    from sqlalchemy import inspect, text
    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()

    # If questions table exists but has no topic_id column → old schema
    needs_reset = False
    if "questions" in existing_tables:
        cols = [c["name"] for c in inspector.get_columns("questions")]
        if "topic_id" not in cols:
            needs_reset = True

    if needs_reset:
        print("Old schema detected — dropping all tables for migration...")
        with engine.connect() as conn:
            conn.execute(text("DROP TABLE IF EXISTS options CASCADE"))
            conn.execute(text("DROP TABLE IF EXISTS questions CASCADE"))
            conn.execute(text("DROP TABLE IF EXISTS topics CASCADE"))
            conn.execute(text("DROP TABLE IF EXISTS categories CASCADE"))
            conn.commit()
        print("Tables dropped. Recreating with new schema...")

    Base.metadata.create_all(bind=engine)
    print("Tables ready.")

seed_data = [
    {
        "name": "AWS Certified Cloud Practitioner",
        "icon": "☁️",
        "color": "#FF9900",
        "topics": [
            {
                "name": "Cloud Concepts",
                "questions": [
                    {
                        "text": "What is the definition of cloud computing?",
                        "options": [
                            {"text": "On-demand delivery of IT resources over the internet", "is_correct": True},
                            {"text": "Storing data on physical hard drives", "is_correct": False},
                            {"text": "Running applications on a local network", "is_correct": False},
                            {"text": "Using USB devices to transfer data", "is_correct": False},
                        ],
                    },
                    {
                        "text": "Which of the following is a benefit of cloud computing?",
                        "options": [
                            {"text": "Fixed capital expenses", "is_correct": False},
                            {"text": "Trade capital expense for variable expense", "is_correct": True},
                            {"text": "Requires managing physical servers", "is_correct": False},
                            {"text": "Limited global reach", "is_correct": False},
                        ],
                    },
                ],
            },
            {
                "name": "AWS Core Services",
                "questions": [
                    {
                        "text": "What is Amazon EC2?",
                        "options": [
                            {"text": "A managed database service", "is_correct": False},
                            {"text": "A virtual server in the cloud", "is_correct": True},
                            {"text": "A content delivery network", "is_correct": False},
                            {"text": "A DNS service", "is_correct": False},
                        ],
                    },
                    {
                        "text": "What is Amazon S3 primarily used for?",
                        "options": [
                            {"text": "Running virtual machines", "is_correct": False},
                            {"text": "Object storage in the cloud", "is_correct": True},
                            {"text": "Relational database management", "is_correct": False},
                            {"text": "Load balancing", "is_correct": False},
                        ],
                    },
                ],
            },
        ],
    },
    {
        "name": "AWS Certified AI Practitioner",
        "icon": "🤖",
        "color": "#232F3E",
        "topics": [
            {
                "name": "AI and ML Fundamentals",
                "questions": [
                    {
                        "text": "What is machine learning?",
                        "options": [
                            {"text": "A type of hardware component", "is_correct": False},
                            {"text": "A subset of AI that learns from data", "is_correct": True},
                            {"text": "A cloud storage service", "is_correct": False},
                            {"text": "A programming language", "is_correct": False},
                        ],
                    },
                    {
                        "text": "What is Amazon SageMaker used for?",
                        "options": [
                            {"text": "Object storage", "is_correct": False},
                            {"text": "Building, training, and deploying ML models", "is_correct": True},
                            {"text": "Virtual networking", "is_correct": False},
                            {"text": "DNS management", "is_correct": False},
                        ],
                    },
                ],
            },
            {
                "name": "Generative AI",
                "questions": [
                    {
                        "text": "What is Amazon Bedrock?",
                        "options": [
                            {"text": "A database service", "is_correct": False},
                            {"text": "A service to build generative AI apps using foundation models", "is_correct": True},
                            {"text": "A storage service", "is_correct": False},
                            {"text": "A compute service", "is_correct": False},
                        ],
                    },
                    {
                        "text": "What does a large language model (LLM) do?",
                        "options": [
                            {"text": "Stores large files", "is_correct": False},
                            {"text": "Generates human-like text based on input", "is_correct": True},
                            {"text": "Manages virtual machines", "is_correct": False},
                            {"text": "Encrypts network traffic", "is_correct": False},
                        ],
                    },
                ],
            },
        ],
    },
    {
        "name": "SQL",
        "icon": "🗄️",
        "color": "#336791",
        "topics": [
            {
                "name": "SQL Basics",
                "questions": [
                    {
                        "text": "Which SQL statement is used to retrieve data?",
                        "options": [
                            {"text": "INSERT", "is_correct": False},
                            {"text": "SELECT", "is_correct": True},
                            {"text": "UPDATE", "is_correct": False},
                            {"text": "DELETE", "is_correct": False},
                        ],
                    },
                    {
                        "text": "Which clause is used to filter rows in SQL?",
                        "options": [
                            {"text": "ORDER BY", "is_correct": False},
                            {"text": "GROUP BY", "is_correct": False},
                            {"text": "WHERE", "is_correct": True},
                            {"text": "HAVING", "is_correct": False},
                        ],
                    },
                ],
            },
            {
                "name": "SQL Joins",
                "questions": [
                    {
                        "text": "What does an INNER JOIN return?",
                        "options": [
                            {"text": "All rows from both tables", "is_correct": False},
                            {"text": "Only matching rows from both tables", "is_correct": True},
                            {"text": "All rows from the left table", "is_correct": False},
                            {"text": "All rows from the right table", "is_correct": False},
                        ],
                    },
                    {
                        "text": "Which join returns all rows from the left table even if no match?",
                        "options": [
                            {"text": "INNER JOIN", "is_correct": False},
                            {"text": "RIGHT JOIN", "is_correct": False},
                            {"text": "LEFT JOIN", "is_correct": True},
                            {"text": "CROSS JOIN", "is_correct": False},
                        ],
                    },
                ],
            },
        ],
    },
    {
        "name": "Docker",
        "icon": "🐳",
        "color": "#2496ED",
        "topics": [
            {
                "name": "Docker Basics",
                "questions": [
                    {
                        "text": "What is a Docker container?",
                        "options": [
                            {"text": "A virtual machine", "is_correct": False},
                            {"text": "A lightweight, standalone executable package", "is_correct": True},
                            {"text": "A cloud storage bucket", "is_correct": False},
                            {"text": "A database instance", "is_correct": False},
                        ],
                    },
                    {
                        "text": "What command builds a Docker image?",
                        "options": [
                            {"text": "docker run", "is_correct": False},
                            {"text": "docker push", "is_correct": False},
                            {"text": "docker build", "is_correct": True},
                            {"text": "docker pull", "is_correct": False},
                        ],
                    },
                ],
            },
            {
                "name": "Docker Compose",
                "questions": [
                    {
                        "text": "What is Docker Compose used for?",
                        "options": [
                            {"text": "Building single containers", "is_correct": False},
                            {"text": "Defining and running multi-container applications", "is_correct": True},
                            {"text": "Managing cloud storage", "is_correct": False},
                            {"text": "Monitoring containers", "is_correct": False},
                        ],
                    },
                    {
                        "text": "What file does Docker Compose use by default?",
                        "options": [
                            {"text": "Dockerfile", "is_correct": False},
                            {"text": "docker-compose.yml", "is_correct": True},
                            {"text": "compose.json", "is_correct": False},
                            {"text": ".dockerignore", "is_correct": False},
                        ],
                    },
                ],
            },
        ],
    },
    {
        "name": "Kubernetes",
        "icon": "☸️",
        "color": "#326CE5",
        "topics": [
            {
                "name": "Kubernetes Basics",
                "questions": [
                    {
                        "text": "What is a Kubernetes Pod?",
                        "options": [
                            {"text": "A physical server", "is_correct": False},
                            {"text": "The smallest deployable unit in Kubernetes", "is_correct": True},
                            {"text": "A storage volume", "is_correct": False},
                            {"text": "A network policy", "is_correct": False},
                        ],
                    },
                    {
                        "text": "What does kubectl get pods do?",
                        "options": [
                            {"text": "Creates new pods", "is_correct": False},
                            {"text": "Lists all running pods", "is_correct": True},
                            {"text": "Deletes pods", "is_correct": False},
                            {"text": "Updates pod configuration", "is_correct": False},
                        ],
                    },
                ],
            },
            {
                "name": "Kubernetes Services",
                "questions": [
                    {
                        "text": "What is a Kubernetes Service?",
                        "options": [
                            {"text": "A way to store data", "is_correct": False},
                            {"text": "An abstraction that exposes pods over a network", "is_correct": True},
                            {"text": "A type of container", "is_correct": False},
                            {"text": "A monitoring tool", "is_correct": False},
                        ],
                    },
                    {
                        "text": "Which Service type exposes an app to external traffic?",
                        "options": [
                            {"text": "ClusterIP", "is_correct": False},
                            {"text": "NodePort", "is_correct": False},
                            {"text": "LoadBalancer", "is_correct": True},
                            {"text": "Headless", "is_correct": False},
                        ],
                    },
                ],
            },
        ],
    },
    {
        "name": "CI",
        "icon": "🔄",
        "color": "#4CAF50",
        "topics": [
            {
                "name": "CI Concepts",
                "questions": [
                    {
                        "text": "What does CI stand for?",
                        "options": [
                            {"text": "Container Integration", "is_correct": False},
                            {"text": "Continuous Integration", "is_correct": True},
                            {"text": "Cloud Infrastructure", "is_correct": False},
                            {"text": "Code Inspection", "is_correct": False},
                        ],
                    },
                    {
                        "text": "What is the main goal of CI?",
                        "options": [
                            {"text": "Deploy to production automatically", "is_correct": False},
                            {"text": "Merge code frequently and detect errors early", "is_correct": True},
                            {"text": "Monitor application performance", "is_correct": False},
                            {"text": "Manage infrastructure as code", "is_correct": False},
                        ],
                    },
                ],
            },
            {
                "name": "CI Tools",
                "questions": [
                    {
                        "text": "Which tool is commonly used for CI pipelines?",
                        "options": [
                            {"text": "Photoshop", "is_correct": False},
                            {"text": "Jenkins", "is_correct": True},
                            {"text": "Excel", "is_correct": False},
                            {"text": "Notepad", "is_correct": False},
                        ],
                    },
                    {
                        "text": "What is a CI pipeline?",
                        "options": [
                            {"text": "A physical network cable", "is_correct": False},
                            {"text": "An automated sequence of build, test, and validate steps", "is_correct": True},
                            {"text": "A type of database", "is_correct": False},
                            {"text": "A container registry", "is_correct": False},
                        ],
                    },
                ],
            },
        ],
    },
    {
        "name": "CD",
        "icon": "📦",
        "color": "#E91E63",
        "topics": [
            {
                "name": "CD Concepts",
                "questions": [
                    {
                        "text": "What does CD stand for in DevOps?",
                        "options": [
                            {"text": "Code Deployment", "is_correct": False},
                            {"text": "Continuous Delivery or Continuous Deployment", "is_correct": True},
                            {"text": "Container Delivery", "is_correct": False},
                            {"text": "Cloud Distribution", "is_correct": False},
                        ],
                    },
                    {
                        "text": "What is the difference between Continuous Delivery and Continuous Deployment?",
                        "options": [
                            {"text": "They are exactly the same", "is_correct": False},
                            {"text": "Delivery requires manual approval; Deployment is fully automatic", "is_correct": True},
                            {"text": "Deployment requires manual approval; Delivery is automatic", "is_correct": False},
                            {"text": "Delivery is only for mobile apps", "is_correct": False},
                        ],
                    },
                ],
            },
            {
                "name": "CD Tools",
                "questions": [
                    {
                        "text": "Which tool is used for CD in AWS?",
                        "options": [
                            {"text": "AWS Lambda", "is_correct": False},
                            {"text": "AWS CodeDeploy", "is_correct": True},
                            {"text": "AWS S3", "is_correct": False},
                            {"text": "AWS CloudFront", "is_correct": False},
                        ],
                    },
                    {
                        "text": "What is a deployment strategy that gradually shifts traffic to a new version?",
                        "options": [
                            {"text": "Big bang deployment", "is_correct": False},
                            {"text": "Canary deployment", "is_correct": True},
                            {"text": "Full rollback", "is_correct": False},
                            {"text": "Cold deployment", "is_correct": False},
                        ],
                    },
                ],
            },
        ],
    },
    {
        "name": "Maven",
        "icon": "📐",
        "color": "#C62828",
        "topics": [
            {
                "name": "Maven Basics",
                "questions": [
                    {
                        "text": "What is Apache Maven?",
                        "options": [
                            {"text": "A database management system", "is_correct": False},
                            {"text": "A build automation tool for Java projects", "is_correct": True},
                            {"text": "A container runtime", "is_correct": False},
                            {"text": "A cloud provider", "is_correct": False},
                        ],
                    },
                    {
                        "text": "What file does Maven use for project configuration?",
                        "options": [
                            {"text": "build.gradle", "is_correct": False},
                            {"text": "package.json", "is_correct": False},
                            {"text": "pom.xml", "is_correct": True},
                            {"text": "Makefile", "is_correct": False},
                        ],
                    },
                ],
            },
            {
                "name": "Maven Lifecycle",
                "questions": [
                    {
                        "text": "Which Maven command compiles and runs tests?",
                        "options": [
                            {"text": "mvn build", "is_correct": False},
                            {"text": "mvn test", "is_correct": True},
                            {"text": "mvn deploy", "is_correct": False},
                            {"text": "mvn run", "is_correct": False},
                        ],
                    },
                    {
                        "text": "What does mvn clean do?",
                        "options": [
                            {"text": "Deploys the app to production", "is_correct": False},
                            {"text": "Removes files generated by previous builds", "is_correct": True},
                            {"text": "Downloads all dependencies", "is_correct": False},
                            {"text": "Runs unit tests", "is_correct": False},
                        ],
                    },
                ],
            },
        ],
    },
]


def seed():
    """Reset schema if needed, create tables, and seed data."""
    reset_tables()

    db = SessionLocal()
    try:
        if db.query(Category).count() > 0:
            print("Database already seeded. Skipping.")
            return

        for cat_data in seed_data:
            category = Category(
                name=cat_data["name"],
                icon=cat_data["icon"],
                color=cat_data["color"],
            )
            db.add(category)
            db.flush()

            for topic_data in cat_data["topics"]:
                topic = Topic(
                    name=topic_data["name"],
                    category_id=category.id,
                )
                db.add(topic)
                db.flush()

                for q_data in topic_data["questions"]:
                    question = Question(
                        text=q_data["text"],
                        topic_id=topic.id,
                    )
                    db.add(question)
                    db.flush()

                    for opt in q_data["options"]:
                        db.add(Option(
                            text=opt["text"],
                            is_correct=opt["is_correct"],
                            question_id=question.id,
                        ))

        db.commit()
        print(f"Seeded {len(seed_data)} categories successfully.")

    except Exception as e:
        db.rollback()
        print(f"Seeding failed: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()
