const bigquery = require('@google-cloud/bigquery')();

// subscribe is the export function
exports.subscribe = function subscribe(event, callback) {
  // The Cloud Pub/Sub Message object.
  const pubsubMessage = event.data;

  // We're just going to log the message to prove that
  // it worked.
  var message=Buffer.from(pubsubMessage.data, 'base64').toString();
  console.log(message);

  var data = JSON.parse(message);
  
  const data2insert = {
    "registry_id": data.registryID,
    "device_id": data.deviceID,
    "heatidx": data.heatidx,
    "humidity": data.humidity,
    "sensor": data.sensor,
    "temperature": data.temperature,
    "sensor_datetime": data.datetime
  };
  
  console.log(data2insert);
  insert2BigQuery(data2insert);
  
  // Don't forget to call the callback.
  callback();
};

function insert2BigQuery(data) {
  const dataset = bigquery.dataset('iotdemo01');
  const table = dataset.table('weather');

  return table.insert(data);
}