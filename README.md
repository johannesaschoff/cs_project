# WeLink Shared Mobility Assistant

## Introduction
WeLink is an innovative shared mobility assistant designed to provide live mobility data for the city of St. Gallen. This application not only allows users to search for real-time shared mobility options but also links them to relevant rental apps. Integrating OpenAI's chat assistant, WeLink offers an interactive and informative experience for users seeking mobility solutions.

## Technology Stack
- Python
- JavaScript
- OpenAI GPT (for chat assistant)
- APIs for accessing shared mobility data

## How to Use
To use WeLink, follow these steps:
1. Clone the repository to your local machine.
2. Install the required dependencies listed in `requirements.txt`.
3. Run `app.py` to start the application.
4. Use the interface to search for live shared mobility options in St. Gallen.
5. Access the chat assistant for additional information and guidance.

## Project Structure

### src (Source Code)
- `app.py`: Main application file.
- `chatbot.py`: OpenAI chat assistant integration.
- `mobilityAPI.py`: Interface with shared mobility data APIs.

### data
- `liveData.json`: Example shared mobility data.

### docs (Documentation)
- `ProjectReport.md`: Comprehensive project report.
- `API_Documentation.md`: Detailed API documentation.

### tests
- `test_app.py`: Application unit tests.
- `test_chatbot.py`: Chatbot functionality tests.
- `test_mobilityAPI.py`: API integration tests.

### .github/workflows
- `ci.yml`: CI setup for automated testing.

### requirements.txt
List of Python packages required for the project.

### LICENSE
Project license file (e.g., MIT License).

### .gitignore
Standard Python .gitignore file.

## Key Features
- **Live Shared Mobility Data**: Real-time mobility data access and display.
- **Rental App Links**: Seamless redirection to mobility rental applications.
- **Chat Assistant**: Integrated OpenAI chat assistant using live data for responses.

## Contributing
We welcome contributions to the WeLink project. Please refer to our contributing guidelines for more information on making pull requests and reporting issues.

## Setup and Installation
For detailed setup and installation instructions, please refer to the `SETUP.md` file in this repository.

## License
This project is licensed under the MIT License - see the [LICENSE.md](LICENSE) file for details.
