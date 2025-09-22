# greenhouse-monitor
# Greenhouse Monitor

Welcome to the **Greenhouse Monitor** project! This repository is designed to help you analyze greenhouse images using advanced AI technology. Whether you're a hobbyist gardener or a professional horticulturist, the Greenhouse Monitor can provide insights into your plants and their environment.

## Table of Contents

- [Project Overview](#project-overview)
- [Key Features](#key-features)
- [Usage](#usage)
- [Installation](#installation)
- [How It Works](#how-it-works)
- [Contribution](#contribution)
- [License](#license)
- [Contact](#contact)

## Project Overview

The Greenhouse Monitor uses OpenAI's GPT-4 Vision to analyze images of plants in a greenhouse setting. By processing these images, the tool identifies plant types, assesses their health, and offers recommendations to improve their growth conditions. This can be a valuable tool for anyone looking to enhance their gardening or farming skills.

## Key Features

- **Plant Identification:** Automatically detects and categorizes various plants in your greenhouse images.
- **Health Assessment:** Evaluates plant health and provides status updates (good, moderate, poor) along with notes on specific issues.
- **Environmental Insights:** Analyzes the conditions of the greenhouse including watering, light, and temperature.
- **JSON Output:** Results are formatted in JSON, making it easy to integrate with other applications or save for future reference.
- **Automatic Reporting:** Generates summary reports of the analyses performed, ensuring you stay informed about your greenhouse's status.

## Usage

To use the Greenhouse Monitor, simply add images of your greenhouse plants in the `images/` directory and push changes to the repository. The system will automatically detect new images, analyze them, and save the results in the `analysis/` directory.

### Example Command

The analysis can also be run manually from the command line as follows:

```bash
python analyze_greenhouse.py path/to/your/image.jpg
```

Make sure to replace `path/to/your/image.jpg` with the actual path of your image file.

## Installation

To set up the Greenhouse Monitor on your local machine, follow these steps:

1. **Clone the Repository:**
   ```bash
   git clone https://github.com/yourusername/greenhouse-monitor.git
   cd greenhouse-monitor
   ```

2. **Install Python Dependencies:**
   Ensure you have Python 3.11 or above installed, then run:
   ```bash
   pip install requests pillow
   ```

3. **Set Up OpenAI API Key:**
   You will need an OpenAI API key to use the analysis feature. Set this in your environment variables:
   ```bash
   export OPENAI_API_KEY='your_api_key_here'
   ```

## How It Works

1. **Image Encoding:** The tool encodes the selected image into Base64 format, which is necessary for transmission to the OpenAI API.
2. **Analysis Prompt:** A structured prompt is created to instruct the AI on how to analyze the plants in the image.
3. **API Interaction:** The system sends a request to the OpenAI API with the provided image and analysis prompt.
4. **Result Parsing:** Upon receiving the response, the tool parses the JSON output, storing useful information in a formatted structure.
5. **Results Storage:** Finally, analysis results are saved as JSON files within the `analysis/` directory, allowing for easy access and review.

## Contribution

We welcome contributions to enhance the functionality of the Greenhouse Monitor. If you have suggestions, improvements, or bug reports, please feel free to open an issue or submit a pull request.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for more details.

## Contact

For further questions or support, please reach out to [your-email@example.com].

---

Thank you for exploring the Greenhouse Monitor! We hope this tool helps you cultivate a thriving greenhouse environment.

---
*README generated from 6 files (2,968 tokens)*