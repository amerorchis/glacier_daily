// trailClosures.js

async function removeDuplicateTrails(trailList) {
const nameLengths = {};

trailList.forEach(item => {
  const name = item.properties.name;
  const coordinates = item.geometry.coordinates;
  const length = coordinates.reduce((sum, coords) => sum + coords.length, 0);

  if (name in nameLengths) {
	if (length > nameLengths[name]) {
	  nameLengths[name] = length;
	}
  } else {
	nameLengths[name] = length;
  }
});

const filteredList = trailList.filter(item => {
  const name = item.properties.name;
  const coordinates = item.geometry.coordinates;
  const length = coordinates.reduce((sum, coords) => sum + coords.length, 0);

  return length > 2 && !name.toLowerCase().includes('cutoff') && length === nameLengths[name];
});

return filteredList.map(item => item.properties);
}

async function closedTrails() {
const url = 'https://carto.nps.gov/user/glaclive/api/v2/sql?format=GeoJSON&q=SELECT%20*%20FROM%20nps_trails%20WHERE%20status%20=%20%27closed%27';

try {
  const response = await fetch(url, { method: 'GET' });
  const status = await response.json();
  const trails = status.features;

  const filteredTrails = await removeDuplicateTrails(trails);
  let closures = [];

  filteredTrails.forEach(i => {
	const name = i.name;
	const reason = i.status_reason ? i.status_reason.replace('CLOSED', 'closed').replace(/\s{2,}/g, ' ') :
	  i.trail_status_info ? i.trail_status_info.replace('CLOSED', 'closed').replace(/\s{2,}/g, ' ') : '';

	const location = i.location;
	const msg = location ? `${name}: ${reason} - ${location}` : `${name}: ${reason}`;
	closures.push({ name, reason, msg });
  });

  const toDelete = [];

  closures.forEach((trail, i) => {
	const { name, reason } = trail;
	if (name && !reason) {
	  const otherListings = closures.reduce((indices, item, index) => {
		if (item.name === name && index !== i && item.reason) {
		  indices.push(index);
		}
		return indices;
	  }, []);

	  if (otherListings.length > 0) {
		toDelete.push(i);
	  }
	}
  });

  toDelete.reverse().forEach(i => closures.splice(i, 1));

  closures.pop();
  closures = closures.map(i => i.msg);

  const indexToRemove = closures.indexOf('Swiftcurrent Pass: Closed Due To Bear Activity');
  if (indexToRemove !== -1) {
	closures.splice(indexToRemove, 1);
  }

  closures = [...new Set(closures)];
  closures = closures.sort();

  if (closures.length > 0) {
	let message = '<ul style="list-style-position: outside;">\n';
	closures.forEach(i => {
	  message += `<li style="line-height: 2em;">${i}</li>\n`;
	});
	document.getElementById('trails_status_container').innerHTML = message + '</ul>';
  } else {
	document.getElementById('trails_status_container').innerHTML = 'There are no trail closures in effect today!';
  }
} catch (error) {
  console.error('Error:', error);
  document.getElementById('trails_status_container').innerHTML = 'An error occurred while fetching trail data.';
}
}

// Call the function when the page loads
closedTrails();