extends Node 

var tilemaps: Array[TileMapLayer] = []
var footstep_player: AudioStreamPlayer
var osc_client: OSCClient
var debug_tile_checks := false
@export_range(1, 30) var cooldown_frames := 5
var cooldown_counter := 0
const OSC_PORT := 4848

const footstep_sounds = {
	"cloud": [
		preload("res://sfx/cloud/cloud-walk-1.mp3"),
		preload("res://sfx/cloud/cloud-walk-2.mp3"),
		preload("res://sfx/cloud/cloud-walk-3.mp3")
		]
}

func _ready() -> void:
	footstep_player = AudioStreamPlayer.new()
	add_child(footstep_player)

	osc_client = OSCClient.new()
	osc_client.ip_address = "127.0.0.1"
	osc_client.port = OSC_PORT
	add_child(osc_client)


func register_tilemap(tilemap: TileMapLayer) -> void:
	if tilemap not in tilemaps:
		tilemaps.append(tilemap)


func unregister_tilemap(tilemap: TileMapLayer) -> void:
	tilemaps.erase(tilemap)


func _prune_freed_tilemaps() -> void:
	tilemaps = tilemaps.filter(func(t): return is_instance_valid(t))


func _physics_process(_delta: float) -> void:
	if cooldown_counter > 0:
		cooldown_counter -= 1

func play_footstep(position: Vector2):
	if cooldown_counter > 0:
		if debug_tile_checks:
			print("[Footstep] cooldown active:", cooldown_counter)
		return

	if debug_tile_checks:
		print("[Footstep] checking world position:", position)

	_send_footstep_osc(get_tile_type(position))


func get_tile_type(position: Vector2) -> String:
	_prune_freed_tilemaps()

	var probe_offsets = [
		Vector2.ZERO,
		Vector2(0, 6),
		Vector2(0, 12),
		Vector2(-4, 8),
		Vector2(4, 8)
	]
	var tile_types = ["cloud", "grass", "dirt", "snow", "mushroom", "water_tube", "leaves"]

	for tilemap in tilemaps:
		for probe in probe_offsets:
			var probe_world = position + probe
			var local_pos = tilemap.to_local(probe_world)
			var tile_position = tilemap.local_to_map(local_pos)
			var data = tilemap.get_cell_tile_data(tile_position)

			if debug_tile_checks:
				print("[Footstep] tilemap=", tilemap.name, " probe=", probe, " local=", local_pos, " cell=", tile_position)

			if data:
				for tile_type in tile_types:
					if data.get_custom_data(tile_type) == tile_type:
						return tile_type

	return "other"


func _send_footstep_osc(str: String) -> void:
	var client := _get_osc_client()
	if client == null:
		push_warning("[Footstep] no OSC client available")
		return

	client.send_message("/player/footstep/" + str, [1])

	if debug_tile_checks:
		print("[Footstep] sent OSC message of type: ", str, " via ", client.name, " port=", client.port, " msg format: /player/footstep/" + str)


func _get_osc_client() -> OSCClient:
	var current_scene := get_tree().current_scene
	if current_scene:
		var player := current_scene.find_child("Player", true, false)
		if player and player.has_node("OSCClient - OUT"):
			return player.get_node("OSCClient - OUT") as OSCClient

	return osc_client
