function exportConfiguration() {

  console.log(formDict());
  var filename ="test.txt";
  var input = JSON.stringify(formDict()); 

  var element = document.createElement('a');
  element.setAttribute('href', 'data:text/plain;charset=utf-8,' + encodeURIComponent(input));
  element.setAttribute('download', filename);

  element.style.display = 'none';
  document.body.appendChild(element);

  element.click();

  document.body.removeChild(element);
}