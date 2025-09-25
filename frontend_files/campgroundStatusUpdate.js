// Update Campground Statuses

async function campgroundAlerts() {
	const url = 'https://carto.nps.gov/user/glaclive/api/v2/sql?format=JSON&q=SELECT%20*%20FROM%20glac_front_country_campgrounds';

	try {
		const response = await fetch(url, { method: 'GET' });
		const status = await response.json();
		const campgrounds = status.rows || [];

		const closures = [];
		const seasonClosures = [];
		const statuses = [];

	for (const campground of campgrounds) {
		const name = campground.name.replace('  ', ' ');

		if (campground.status === 'closed' && campground.service_status.includes('season')) {
			seasonClosures.push(name);
		} else if (campground.status === 'closed') {
			closures.push(`${name} CG: currently closed.`);
		}

		const notice = campground.description.toLowerCase();
		if (notice.includes('camping only') || notice.includes('posted')) {
			const cleanedNotice = campground.description.replace(/ <br><br><a href="https:\/\/www.nps.gov\/glac\/planyourvisit\/reservation-campgrounds.htm" target="_blank">Campground Details<\/a><br><br>/g, '');
			const formattedNotice = cleanedNotice.replace(/<b>/g, '').replace(/<\/b>/g, '');
			const capitalizedNotice = formattedNotice.split('. ').map(sentence => sentence.charAt(0).toUpperCase() + sentence.slice(1)).join('. ');
			statuses.push(`${name} CG: ${capitalizedNotice}`);
		}
	}

		const uniqueStatuses = [...new Set(statuses)];
		const uniqueClosures = [...new Set(closures)];
		const uniqueSeasonClosures = [...new Set(seasonClosures)];

		const sortedStatuses = uniqueStatuses.sort();
		const sortedClosures = uniqueClosures.sort();
		const sortedSeasonClosures = uniqueSeasonClosures.sort();

		sortedStatuses.push(...sortedClosures);

		if (sortedSeasonClosures.length > 0) {
			const seasonal = [`Closed for the season: ${sortedSeasonClosures.join(', ')}`];
			sortedStatuses.push(...seasonal);
		}

		if (sortedStatuses.length > 0) {
			const message = '<ul style="list-style-position: outside;">\n';
			const formattedMessage = sortedStatuses.map(item => `<li style="line-height: 2em;">${item}</li>\n`).join('');
			const finalMessage = message + formattedMessage + '</ul>';

			document.getElementById('campground-status').innerHTML = finalMessage;
		} else {
			document.getElementById('campground-status').innerHTML = '';
		}
	} catch (error) {
		console.error('Error:', error.message);
		document.getElementById('campground-status').innerHTML = 'An error occurred while fetching campground information.';
	}
}

// Call the function when the page loads
campgroundAlerts();
