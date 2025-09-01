# GitHub OAuth Test Application

This application is a simple command-line tool that demonstrates the GitHub OAuth2 authorization code flow. It generates a unique URL for you to authorize against your GitHub account. Upon successful authorization, it retrieves an OAuth access token from GitHub and prints it to the console.

## Prerequisites

- Python 3
- The `httpx` library (`pip install httpx`)

## Getting Started: Obtaining GitHub Credentials

Before you can use this application, you need to register it as a new OAuth application in your GitHub account to get a **Client ID** and **Client Secret**.

1.  **Go to GitHub Developer Settings:**
    *   Navigate to [https://github.com/settings/developers](https://github.com/settings/developers) in your web browser.

2.  **Create a New OAuth App:**
    *   Click on the "**New OAuth App**" button.

3.  **Fill out the form:**
    *   **Application name:** You can enter any name, for example, `My Local Test App`.
    *   **Homepage URL:** `http://localhost:8080`
    *   **Authorization callback URL:** `http://localhost:8080/callback`

4.  **Register the application:**
    *   Click the "**Register application**" button.

Once registered, you will be presented with your **Client ID** and a button to generate a **Client Secret**. Copy both of these credentials to use when running the application.

## Usage

1.  Run the application from your terminal:
    ```bash
    python3 app.py
    ```

2.  The application will prompt you to enter your **Client ID** and **Client Secret**.

3.  After you provide your credentials, the script will output a URL. Copy and paste this URL into your web browser.

4.  Authorize the application on the GitHub page.

5.  After authorization, you will be redirected to a local URL, and the application will receive the access token and print it in your terminal before exiting.

## Example

Here is an example of the application flow:

```
(venv) @-MacBook-Air ouath-test % python3 Downloads/l8e_harbor/ouath-test/app.py

Enter your GitHub OAuth Client ID: <id>
Enter your GitHub OAuth Client Secret:
Please open the following URL in your browser to authorize the application:
https://github.com/login/oauth/authorize?client_id=<id>&redirect_uri=http://localhost:8080/callback&scope=repo,user

Waiting for authentication callback on port 8080...
127.0.0.1 - - [01/Sep/2025 15:33:55] "GET /callback?code=<token> HTTP/1.1" 200 -
Authorization code received: <token>

GitHub Access Token: gho_<token>
Application exiting.
```
