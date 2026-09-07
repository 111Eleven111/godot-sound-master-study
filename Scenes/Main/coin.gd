extends Area2D

var osc_client: OSCClient
const OSC_PORT := 4848

func _ready() -> void:
	osc_client = OSCClient.new()
	osc_client.ip_address = "127.0.0.1"
	osc_client.port = OSC_PORT
	add_child(osc_client)

func _get_osc_client() -> OSCClient:
	var current_scene := get_tree().current_scene
	if current_scene:
		var player := current_scene.find_child("Player", true, false)
		if player and player.has_node("OSCClient - OUT"):
			return player.get_node("OSCClient - OUT") as OSCClient

	return osc_client

func _send_coin_sfx_osc() -> void:
	var client := _get_osc_client()
	if client:
		client.send_message("/coin/collected", [1])


func _on_body_entered(body: Node2D) -> void:
	print("test")
	if body.is_in_group("Player"):
		var player := body as Player
		if player == null:
			return

		player.score += 1
		player.log_coin_collected(name, player.score)
		self.queue_free()
		print(player.score)

		# Send OSC message to indicate coin collection
		_send_coin_sfx_osc()
