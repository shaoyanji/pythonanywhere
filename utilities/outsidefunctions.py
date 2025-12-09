@app.route("/", methods=["GET", "POST"])
def hello_world():
    if request.method == "GET":
        command = ["ls"]
        result = subprocess.run(command, check=True, text=True, capture_output=True)
        return mdeee(result.stdout)

    elif request.method == "POST":
        data = request.get_json()  # Get JSON data from the request body
        if data:
            # Extract 'name' from JSON, default to 'Unknown'
            name = data.get("name", "Unknown")
            # 200 OK status code

            return (
                jsonify(
                    {"message": f"Hello, {name}! This is a POST request with data."}
                ),
                200,
            )
        else:
            # 400 Bad Request
            return (
                "Hello, World! This is a POST request, but no data was provided.",
                400,
            )
    else:
        return "Method not allowed.", 405  # 405 Method Not Allowed


@app.route("/echo", methods=["POST"])
def echo():
    data = request.get_json()
    if data:
        return jsonify(data), 200  # Just return the same data you received
    else:
        return "No data provided to echo.", 400
