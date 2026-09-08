extends Area2D

var platform_debug := false

func _on_body_entered(body: Node2D):
	if body.is_in_group("Player"):
		body.last_landed_tiles.push_back([name, global_position])
		body._check_tile_id_on_land()
		if platform_debug:
			print("PLATFORM TEST: ", name, global_position)
		
