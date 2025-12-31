 OutfitAI — AI-Based Outfit Recommender
OutfitAI is an AI-powered outfit recommendation system that analyzes the colors in a clothing image and generates compatible outfit suggestions. By combining image processing, machine learning, and generative AI, the project provides fast and accurate outfit guidance to users.

1. Project Overview
Choosing an outfit can be time-consuming and confusing. Many users struggle with color harmony and matching their clothing pieces.
OutfitAI addresses this problem by automatically analyzing an uploaded clothing photo and generating personalized outfit recommendations based on dominant colors.

 2. Project Goals
•	Reduce the time required for outfit selection
•	Provide AI-generated and personalized outfit suggestions
•	Automate color extraction and interpretation from clothing images
•	Integrate machine learning and generative AI models into a web-based platform
•	Deliver a simple, fast, and user-friendly experience

 3. Process Flow
1.	The user uploads a clothing image
2.	FastAPI receives the image
3.	PIL + NumPy perform image preprocessing
4.	Scikit-learn (K-Means) extracts dominant colors
5.	Dominant colors are sent to Google Gemini API
6.	Gemini generates outfit suggestions
7.	The frontend displays the results to the user

 4. Technologies Used
Category	Technologies
Backend	FastAPI (Python)
Machine Learning	Scikit-learn (K-Means Clustering)
Image Processing	PIL (Pillow), NumPy
Artificial Intelligence	Google Gemini API
Frontend	HTML, CSS, JavaScript
Version Control	Git, GitHub

 5. Installation & Setup
1. Clone the repository
git clone https://github.com/afracayann/OutfitAI.git
cd OutfitAI
2. Install dependencies
pip install -r requirements.txt
3. Start the backend server
uvicorn main:app --reload
4. Access the application
http://localhost:8000

 6. API Usage
POST /predict
Uploads an image, analyzes colors, and returns AI-generated outfit recommendations.
Example Response
{
  "dominant_colors": ["#a2b4c9", "#7d8fa3"],
  "suggestions": "These colors pair well with beige and navy. Consider combining this piece with dark jeans and neutral accessories."
}

 7. How It Works
•	Extracts dominant colors from the uploaded image
•	Processes color values using K-Means clustering
•	Sends the extracted palette to the Gemini API
•	Receives and displays AI-generated outfit suggestions

 8. Developers
•	Afra Çayan — 210204011
•	Neslihan Yıldız — 210204017

 Conclusion
OutfitAI demonstrates how AI technologies can automate outfit selection by analyzing colors and generating style suggestions. The system uses image processing, clustering algorithms, and generative AI to provide fast and practical outfit recommendations.


