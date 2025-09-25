<?php
// Set the appropriate content type
header('Content-Type: application/json');

// Set the time zone to Mountain Time
date_default_timezone_set('America/Denver');

// Calculate the remaining time until midnight Mountain Time
$now = new DateTime('now', new DateTimeZone('America/Denver'));
$midnight = new DateTime('tomorrow', new DateTimeZone('America/Denver'));
$midnight->setTime(0, 0, 0);
$interval = $now->diff($midnight);
$maxAgeSeconds = $interval->s + ($interval->i * 60) + ($interval->h * 3600);

// Set cache control headers with dynamic max-age value
header('Cache-Control: public, max-age=' . $maxAgeSeconds);

// Read the JSON data from the file
$jsonData = file_get_contents('email.json');
$data = json_decode($jsonData, true);

// Check if 'date' key exists and matches today's date
if (isset($data['date']) && $data['date'] === date('Y-m-d')) {
  // Output the JSON data
  echo $jsonData;
} else {
  // Return an error message
  http_response_code(404);
  $errorMessage = array('error' => 'Data not available for today, data is from ' . $data[date] . ' not from ' . date('Y-m-d') . '. (Dates in Mountain Time.)');
  echo json_encode($errorMessage);
}
?>
