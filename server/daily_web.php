<?php

// Set content type to JSON
header('Content-Type: application/json');

// Set cache control headers to expire in 1 hour
header('Cache-Control: no-store, no-cache, must-revalidate, private, max-age=3600');

$jsonData = file_get_contents('web.json');
$data = json_decode($jsonData, true);

// Output the JSON data
echo json_encode($data);

?>
