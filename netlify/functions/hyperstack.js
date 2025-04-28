const axios = require('axios');

const API_BASE_URL = "https://infrahub-api.nexgencloud.com/v1";
// IMPORTANT: Set HYPERSTACK_API_KEY environment variable in your Netlify site settings!
const API_KEY = process.env.HYPERSTACK_API_KEY;

exports.handler = async (event, context) => {
  // Allow only POST requests from the frontend (axios sends data in the body)
  if (event.httpMethod !== 'POST') {
    return { statusCode: 405, body: 'Method Not Allowed' };
  }

  if (!API_KEY) {
     console.error("HYPERSTACK_API_KEY environment variable not set.");
     return { statusCode: 500, body: JSON.stringify({ error: 'Server configuration error: API key missing.' }) };
  }

  let requestData;
  try {
    requestData = JSON.parse(event.body);
  } catch (error) {
    return { statusCode: 400, body: JSON.stringify({ error: 'Invalid request body.' }) };
  }

  const { targetPath, targetMethod, payload } = requestData;

  if (!targetPath || !targetMethod) {
      return { statusCode: 400, body: JSON.stringify({ error: 'Missing targetPath or targetMethod in request.' }) };
  }

  // Basic validation to prevent open proxy (only allow expected paths)
  if (!targetPath.startsWith('/core/virtual-machines')) {
      console.warn(`Blocked attempt to access unexpected path: ${targetPath}`);
      return { statusCode: 403, body: JSON.stringify({ error: 'Access to this API path is forbidden.' }) };
  }

  const targetUrl = `${API_BASE_URL}${targetPath}`;
  const method = targetMethod.toLowerCase(); // Ensure method is lowercase

  console.log(`Proxying request: ${method.toUpperCase()} ${targetUrl}`); // Log the proxied request

  try {
    const response = await axios({
      method: method,
      url: targetUrl,
      headers: {
        accept: 'application/json',
        api_key: API_KEY, // Use the secure environment variable
        // Forward other relevant headers if needed, but avoid forwarding all headers
      },
      data: payload, // Pass payload for methods like POST, PUT
      timeout: 10000 // Add a timeout (10 seconds)
    });

    return {
      statusCode: response.status,
      body: JSON.stringify(response.data),
      headers: {
          'Content-Type': 'application/json'
      }
    };
  } catch (error) {
    console.error(`Error calling Hyperstack API: ${method.toUpperCase()} ${targetUrl}`, error.response?.data || error.message);

    // Return the error status and message from the target API if possible
    const statusCode = error.response?.status || 500;
    const errorMessage = error.response?.data?.message || error.response?.data?.error || error.message || 'An unknown error occurred while contacting the Hyperstack API.';

    return {
      statusCode: statusCode,
      body: JSON.stringify({ error: errorMessage }),
       headers: {
          'Content-Type': 'application/json'
      }
    };
  }
}; 