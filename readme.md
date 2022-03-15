Pulls data from hwinfo server and exposes it as JSON.

Simple HTML frontend tailored to use on phone screens included.

You need:
- hwinfo running with its server feature enabled
- python available on your system

Hit run.bat and access http://<your_desktop_ip>:8000 from your phone.

You can customize which properties to show on the frontend. Just edit `index.html` and refresh the page.
To see all available properties access http://localhost:8000/data.

Thanks to Felix Oghină for the original script
https://medium.com/swlh/reverse-engineering-a-tcp-protocol-455d248d68fa
