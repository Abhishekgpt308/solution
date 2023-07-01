import os
from flask import Flask, jsonify, request
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from sqlalchemy import create_engine, Column, String, Integer
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm.exc import NoResultFound

# Create Flask app
app = Flask(__name__)

# Configure database
DB_HOST = 'localhost'
DB_PORT = 5432
DB_NAME = 'mydatabase'
DB_USER = 'myuser'
DB_PASSWORD = 'mypassword'
DB_URI = f'postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}'
engine = create_engine(DB_URI)
Base = declarative_base()
Session = sessionmaker(bind=engine)


# Define Document model
class Document(Base):
    __tablename__ = 'documents'

    id = Column(Integer, primary_key=True)
    name = Column(String)
    content = Column(String)


# Initialize Google Drive API client
SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
SERVICE_ACCOUNT_FILE = 'path/to/service_account.json'  # Update with your service account credentials file path
credentials = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
drive_service = build('drive', 'v3', credentials=credentials)


@app.route('/documents', methods=['GET'])
def get_documents():
    """
    Get a list of documents from Google Drive.
    """
    try:
        response = drive_service.files().list(q="mimeType='application/pdf'",
                                              fields="files(id, name)").execute()
        documents = response.get('files', [])
        return jsonify(documents), 200
    except HttpError as e:
        return jsonify({'error': str(e)}), e.status_code


@app.route('/documents/<document_id>', methods=['GET'])
def get_document_content(document_id):
    """
    Get the content of a document by its ID.
    """
    try:
        response = drive_service.files().export_media(fileId=document_id, mimeType='text/plain').execute()
        content = response.decode('utf-8')
        return jsonify({'content': content}), 200
    except HttpError as e:
        return jsonify({'error': str(e)}), e.status_code


@app.route('/documents/query', methods=['POST'])
def query_documents():
    """
    Perform a natural language query on the documents.
    """
    query = request.json.get('query', '')

    # Validate input
    if not query:
        return jsonify({'error': 'Query is required.'}), 400

    try:
        session = Session()
        result = session.query(Document).filter(Document.content.ilike(f'%{query}%')).all()
        documents = [{'id': doc.id, 'name': doc.name} for doc in result]
        return jsonify(documents), 200
    except SQLAlchemyError as e:
        return jsonify({'error': str(e)}), 500
    finally:
        session.close()


if __name__ == '__main__':
    # Create tables if they don't exist
    Base.metadata.create_all(engine)
    app.run()
