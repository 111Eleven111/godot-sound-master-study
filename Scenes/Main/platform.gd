extends Area2D

var platform_debug := false

func _on_body_entered(body: Node2D):
	if body.is_in_group("Player"):
		if platform_debug:
			print("PLATFORM TEST: ", name, global_position)
		
