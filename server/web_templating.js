document.addEventListener('DOMContentLoaded', function () {
// Fetch the JSON data
    fetch(`/daily/api/daily_web`)
        .then(response => response.json())
        .then(data => {
            // Get the content container
            const contentContainer = document.getElementById('content');
            
            // Iterate through each key in the JSON
            Object.keys(data).forEach(key => {
                // Create a regular expression to match the placeholders like {{ key }}
                const regex = new RegExp('{{\\s*' + key + '\\s*}}', 'g');

                // Base64 decode the value
                const decodedValue = decodeBase64(data[key]);
                console.log(decodedValue);

                // Strip HTML tags from the decoded value while preserving <ul> and <li> tags
                const sanitizedValue = stripHtmlTags(decodedValue);

                // Replace the placeholders with the sanitized values
                contentContainer.innerHTML = contentContainer.innerHTML.replace(regex, sanitizedValue);

                // Check if the value is empty and remove the corresponding div
                if (data[key].trim() === '' && document.getElementById(key)) {
                    document.getElementById(key).remove();
                }
            });
        })
        .catch(error => console.error('Error fetching JSON:', error));

    // Function to strip HTML tags while preserving <ul> and <li> tags
    function stripHtmlTags(html) {
        const doc = new DOMParser().parseFromString(html, 'text/html');

        // Iterate through all elements and remove inline styles
        doc.querySelectorAll('*').forEach(element => {
            element.removeAttribute('style');
        });

        return doc.body.innerHTML;
    }

    // Function to decode base64 with error handling
    function decodeBase64(value) {
        try {
            return atob(value);
        } catch (error) {
            console.error('Error decoding base64:', error);
            return value; // Return the original value if decoding fails
        }
    }
});