class_name Player
extends CharacterBody2D

# debug
var debug_osc_msg = false


# Player node references
@onready var coyote_timer = $CoyoteTimer
@onready var jump_buffer_timer = $JumpBufferTimer
@onready var jump_trojectory_line = $JumpTrojectoryLine

# UI node references
@onready var timer_label = $UILayer/TimerLabel
@onready var status_label = $UILayer/StatusLabel
@onready var score_label = $UILayer/ScoreLabel
@onready var coin_counter_label = $UILayer/CoinCounterLabel

# Audio nodes are optional - may not exist in all scenes
var jump_sfx_1: AudioStreamPlayer
var land_sfx_1: AudioStreamPlayer
var jump_sfx_1_vari: AudioStreamPlayer
var land_sfx_1_vari: AudioStreamPlayer
var wind_sfx: AudioStreamPlayer
var wind_modulation_timer := 0.1
var wind_modulation_target_db := 0.5
var wind_modulation_target_pitch := 1.5
var wind_modulation_target_pan := 0.0

# MAX SDT variation variables
const JUMP_VARI_BUS := "JumpVariPanBus"
const LAND_VARI_BUS := "LandVariPanBus"
const WIND_VARI_BUS := "WindVariPanBus"

var jump_vari_panner: AudioEffectPanner
var land_vari_panner: AudioEffectPanner
var wind_vari_panner: AudioEffectPanner


# player state variables
var was_on_floor := false
var reset := false
var walking_frame_count := 0
var walking_tile_type := ""

# Timer tracking
var elapsed_time := 0.0
var is_timer_running := false
var start_position := Vector2.ZERO
var victory_height := 10000
var victory_reached := false

# Score tracking
var score := 0

# Jump tracking for variable jump height
var is_jump_held := false
var jump_hold_boost := 0.0
var max_jump_hold_boost := 200.0  # Additional velocity boost from holding

var prev_jump_height := 0.0
var peak_reached := false

# audio toggles
var master_bus_muted := false

# Study telemetry / session logging
var telemetry_session_active := false
var telemetry_file: FileAccess
var telemetry_file_path := ""
var telemetry_session_id := ""

@export_group("Movement")
## Maximum speed reachable by player
@export_range(0, 500) var max_speed := 180.0
## Minimum speed when variable_min_speed is set to true & min_speed isn't 0
@export_range(0, 500) var min_speed := 0.0
## Acceleration while on the ground (how quickly the player reaches max speed)
@export_range(0, 500) var acceleration := 20.0
## Friction while on group (how quickly the player slows down)
@export_range(0, 50) var friction := 50.0
## Acceleration while in the air (how quickly the player reaches max speed)
@export_range(0, 500) var air_acceleration := 9.0
## Air friction while in the air (how quickly the player slows down)
@export_range(0, 50) var air_resistance := 50.0
## Sets a variable max speed depending on how far the joystick is pushed
@export var is_variable_max_speed := false
## sets a minimum speed based on min_speed
@export var is_variable_min_speed := false

@export_group("Jump Assist")
## Max amount of time allowed after leaving the ground while still being able to jump
@export_range(0, 1) var coyote_timer_value = 0.1
## Max amount of time the game holds on to the players input to accecute when avaiable
@export_range(0, 1) var jump_buffer_timer_value = 0.15


@export_group("Jump")
## Max jump height
@export var jump_height := 100
## Amount of time it takes the player to reach the peak of their jump
@export var jump_time_to_peak := 0.4
## Amount of time it takes the player to fall from the peak of their jump to the ground
@export var jump_time_to_descent := 0.3
## Determains if a player jump highet changes depending on how long they held it in
@export var variable_jump_height := true
## Determains the minumum jump heighet a player can reach if they barely tap the jump button (and variable_jump_height is true)
@export var minimum_jump_height := 100

@export_group("Jump Trojectory")
## Maximum amount of points used to visualize player's jump trojectory (WiP)
@export var max_trojectory_ponints := 100

@export_group("Audio - Folio (SDT)")
## Maximum fall speed for impact energy calculation
@export_range(100, 1000) var max_fall_speed := 500.0
## Current surface type for folio synthesis (wood, stone, metal, etc.)
@export var current_surface_tag := "wood"
## Downward offset from player origin to approximate feet contact for footstep tile checks
@export_range(0, 64) var footstep_probe_down := 14.0


# set velocity/gravity
@onready var jump_velocity : float = (2.0 * jump_height) / jump_time_to_peak * -1
@onready var jump_gravity : float = (-2.0 * jump_height) / (jump_time_to_peak * jump_time_to_peak) * -1
@onready var fall_gravity : float = (-2.0 * jump_height) / (jump_time_to_descent * jump_time_to_descent) * -1


# scene rules
@export_group("Scene Rules")
@export var jump_enabled_scenes: PackedStringArray = PackedStringArray([
	"res://Scenes/Main/main.tscn",
	"res://Scenes/Main/scene-1.tscn",
	"res://Scenes/Main/scene-2.tscn",
	"res://Scenes/Main/scene-3.tscn",
	"res://Scenes/Main/scene-4.tscn",
	"res://Scenes/Main/scene-5.tscn",
	"res://Scenes/Main/scene-6.tscn",
	"res://Scenes/Main/scene-7.tscn"
])
## Scenes where Godot AudioStreamPlayers are muted (OSC/MAX output is unchanged)
@export var godot_muted_scenes: PackedStringArray = PackedStringArray([
	"res://Scenes/Main/scene-1.tscn",
	"res://Scenes/Main/scene-2.tscn",
	"res://Scenes/Main/scene-3.tscn",
	"res://Scenes/Main/scene-4.tscn"
])
@export var scene_shortcuts: PackedStringArray = PackedStringArray([
	"res://Scenes/Main/scene-1.tscn",
	"res://Scenes/Main/scene-2.tscn",
	"res://Scenes/Main/scene-3.tscn",
	"res://Scenes/Main/scene-4.tscn",
	"res://Scenes/Main/scene-5.tscn",
	"res://Scenes/Main/scene-6.tscn",
	"res://Scenes/Main/scene-7.tscn"
])

func _ready():
	coyote_timer.wait_time = coyote_timer_value
	jump_buffer_timer.wait_time = jump_buffer_timer_value
	start_position = global_position
	victory_height = -1973
	_update_timer_display()
	_set_prompt_ui()
	reset = true

	# Try to load audio nodes if they exist
	if has_node("jump_sfx_1"):
		jump_sfx_1 = $jump_sfx_1
	if has_node("land_sfx_1"):
		land_sfx_1 = $land_sfx_1
	if has_node("jump_sfx_1_vari"):
		jump_sfx_1_vari = $jump_sfx_1_vari
	if has_node("land_sfx_1_vari"):
		land_sfx_1_vari = $land_sfx_1_vari
	if has_node("WindSFX"):
		wind_sfx = $WindSFX
	elif has_node("wind_sfx"):
		wind_sfx = $wind_sfx

	if wind_sfx:
		wind_sfx.volume_db = -40.0

	_configure_scene_variation_audio()
	_initialize_telemetry_for_current_scene()
	_apply_godot_scene_mute()

func _exit_tree():
	if telemetry_session_active:
		_stop_telemetry_session("scene_unload")

func _initialize_telemetry_for_current_scene() -> void:
	var current_scene_path := ""
	if get_tree().current_scene:
		current_scene_path = get_tree().current_scene.scene_file_path

	if current_scene_path.ends_with("scene-1.tscn"):
		_start_telemetry_session()

func _start_telemetry_session() -> void:
	if telemetry_session_active:
		return

	var telemetry_dir := "user://telemetry"
	var dir_access := DirAccess.open("user://")
	if dir_access and not dir_access.dir_exists("telemetry"):
		dir_access.make_dir_recursive("telemetry")

	var timestamp := Time.get_datetime_string_from_system().replace(":", "-").replace(" ", "_")
	telemetry_session_id = "session_" + timestamp
	telemetry_file_path = telemetry_dir + "/" + telemetry_session_id + ".csv"
	telemetry_file = FileAccess.open(telemetry_file_path, FileAccess.WRITE)
	if telemetry_file == null:
		push_error("Could not open telemetry log: %s (error %s)" % [telemetry_file_path, FileAccess.get_open_error()])
		return

	telemetry_session_active = true
	_write_telemetry_row(["timestamp_seconds", "event", "x", "y", "velocity_x", "velocity_y", "action", "info"])
	_log_telemetry_event("session_start", {"scene": _current_scene_path()})
	print("Telemetry started: ", telemetry_file_path)

func _stop_telemetry_session(reason: String = "scene_change") -> void:
	if not telemetry_session_active:
		return

	_log_telemetry_event("session_end", {"reason": reason})
	if telemetry_file:
		telemetry_file.flush()
		telemetry_file = null
	telemetry_session_active = false
	print("Telemetry stopped: ", telemetry_file_path, " reason: ", reason)

func _current_scene_path() -> String:
	if get_tree().current_scene:
		return get_tree().current_scene.scene_file_path
	return ""

func _csv_escape(value) -> String:
	var text := String(value)
	text = text.replace("\"", "\"\"")
	if text.find(",") != -1 or text.find("\n") != -1 or text.find("\"") != -1:
		text = "\"" + text + "\""
	return text

func _write_telemetry_row(row: Array) -> void:
	if telemetry_file == null:
		return
	var csv_line := ""
	for i in range(row.size()):
		if i > 0:
			csv_line += ","
		csv_line += _csv_escape(row[i])
	telemetry_file.store_line(csv_line)

func _log_telemetry_event(event_name: String, data: Dictionary = {}) -> void:
	if not telemetry_session_active or telemetry_file == null:
		return

	var mac_time := float(Time.get_ticks_msec()) / 1000.0
	var row := [
		str(mac_time),
		event_name,
		str(position.x),
		str(position.y),
		str(velocity.x),
		str(velocity.y),
		String(data.get("action", "")),
		String(data.get("info", ""))
	]
	_write_telemetry_row(row)

func log_coin_collected(coin_id: String, new_score: int) -> void:
	_log_telemetry_event("coin_collected", {
		"action": "collect_coin",
		"info": "coin_%s_score_%d" % [coin_id, new_score]
	})

func log_external_telemetry_event(event_name: String, value_text: String) -> void:
	_log_telemetry_event(event_name, {
		"action": "osc_received",
		"info": "value_%s" % value_text
	})


# Sets the gravity depending on the context
func _get_gravity(_velocity):
	return jump_gravity if _velocity.y < 0.0 else fall_gravity


# Calculates the players movement depending on the context
func _get_movement(fric: float, accel: float, delta: float):
	var direction = Input.get_axis("Move_Left", "Move_Right")

	if direction:
		velocity.x += sign(direction) * accel * delta * 100
	
	if !direction or sign(direction) != sign(velocity.x):
		velocity.x = move_toward(velocity.x, 0, fric * delta * 100)
	
	if is_variable_max_speed:
		velocity.x = clamp(velocity.x, -max_speed * abs(direction), max_speed * abs(direction))
	else:
		velocity.x = clamp(velocity.x, -max_speed, max_speed)
	
	if is_variable_min_speed and min_speed > 0:
			velocity.x = maxf(abs(velocity.x), abs(min_speed * sign(direction))) * sign(direction)

# A way to visialize the players jump trojectory in real time (WiP)
func _projected_jump_trojectory(_delta, direction):
	var max_points = max_trojectory_ponints
	
	jump_trojectory_line.clear_points()
	var pos := Vector2.ZERO
	var vel := Vector2(max_speed * direction, jump_velocity)
	for point in max_points:
		jump_trojectory_line.add_point(pos)
		vel.y += _get_gravity(vel) * _delta
		pos += vel * _delta


# Flips the player sprite depending on their movemnt direction
func _set_sprite_direction(direction: int) -> void:
	if direction > 0.0:
		$AnimatedSprite2D.flip_h = true

	if direction < 0.0:
		$AnimatedSprite2D.flip_h = false


# Physics process handles player movement, jumping, and audio updates
func _physics_process(delta):
	
	# while airborne:
	if not is_on_floor():
		velocity.y += _get_gravity(velocity) * delta
		
		# fast fall
		# if Input.is_action_just_pressed("Move_Down"):
			
		#	if peak_reached:
		#		velocity.y = velocity.y * 3
		#	else:
		#		velocity.y = velocity.y * -3
		
		_get_movement(air_resistance, air_acceleration, delta)

		# SDT wind procsesing
		_sdt_wind()

		# check if player collides mid air and send a bang to MAX/SDT for folio synthesis
		if _is_on_wall():
			$"OSCClient - OUT".send_message("/player/collided", [1])

		# check if we have reached peak of jump
		# print(global_position[1])
		# print("test: ", global_position[1], "    " ,prev_jump_height)

		if global_position[1] > prev_jump_height and not peak_reached:
			print("Peak reached")
			peak_reached = true
			
		prev_jump_height = global_position[1]

	else:
		if coyote_timer.is_stopped():
			coyote_timer.start()
		if jump_buffer_timer.time_left > 0.0:
			jump_buffer_timer.stop()
			jump()
		_get_movement(friction, acceleration, delta)

	_update_wind_sfx(delta)
	
	_set_sprite_direction(sign(velocity.x))
	
	if Input.is_action_just_pressed("Move_Left"):
		_log_telemetry_event("move_left_pressed", {"action": "Move_Left", "info": "pressed"})
	if Input.is_action_just_pressed("Move_Right"):
		_log_telemetry_event("move_right_pressed", {"action": "Move_Right", "info": "pressed"})
	if Input.is_action_just_pressed("Jump"):
		_log_telemetry_event("jump_input_pressed", {"action": "Jump", "info": "pressed"})
		jump()
	
	if Input.is_action_just_released("Jump"):
		_log_telemetry_event("jump_input_released", {"action": "Jump", "info": "released"})
		jump_cut()
	
	# Add boost to jump velocity while jump is held (variable jump height)
	if is_jump_held and Input.is_action_pressed("Jump") and variable_jump_height:
		if velocity.y < 0.0:  # Only boost while going upward
			jump_hold_boost += 200.0 * delta  # Boost accumulation rate
			jump_hold_boost = clamp(jump_hold_boost, 0.0, max_jump_hold_boost)
			velocity.y -= jump_hold_boost * delta
	
	# Start timer on first keyboard input (movement or jump)
	if not is_timer_running and (Input.is_action_pressed("Move_Left") or Input.is_action_pressed("Move_Right") or Input.is_action_pressed("Jump")) and reset:
		is_timer_running = true
		reset = false
		_set_running_ui()
		print("Timer started on input!")
	
	# Update timer if running
	if is_timer_running:
		elapsed_time += delta
		_update_timer_display()
		
		# Check if player reached victory height
		if position.y <= victory_height:
			_on_victory()
	
	if is_on_floor() and absf(velocity.x) > 0.1:
		$AnimatedSprite2D.play("walk")
		# $"OSCClient - OUT".send_message("/player/velocity", [velocity.x])

		# every 5th frame, play footstep sound
		walking_frame_count += 1
		if walking_frame_count % 5 == 0:
			_play_footstep()
	else:
		walking_frame_count = 0
		$AnimatedSprite2D.play("idle")
		# $"OSCClient - OUT".send_message("/player/velocity", [0])

	# update coin score display
	coin_counter_label.text = str(score)
		
#	if Input.is_action_just_pressed("Preview_Jump"):
#		_projected_jump_trojectory(delta, sign(velocity.x))
	
	# Capture velocity before move_and_slide() resets it
	var pre_landing_velocity = velocity
	
	move_and_slide()
	_walking_on_tile()
	
	# Check if player just landed (velocity.y is now 0 after move_and_slide)
	if not was_on_floor and is_on_floor():
		is_jump_held = false
		jump_hold_boost = 0.0
		_on_landed(pre_landing_velocity, current_surface_tag)
	
	was_on_floor = is_on_floor()


func _unhandled_input(event):
	# switch scene
	if event is InputEventKey and event.pressed and not event.echo:
		var scene_index := _get_scene_shortcut_index(event.keycode)
		if scene_index != -1:
			if scene_index == 9:  # 0 key - reset player position and timer
				_reset_player()
			else:
				_switch_to_scene(scene_index)
				
		
		# mute godot audio master
		if event.keycode == KEY_M:
			if _is_godot_muted_in_current_scene():
				return
			if master_bus_muted:
				AudioServer.set_bus_volume_db(0, -2)
				master_bus_muted = false
			else:
				AudioServer.set_bus_volume_db(0, -INF)
				master_bus_muted = true


func _get_scene_shortcut_index(keycode: Key) -> int:
	if keycode >= KEY_1 and keycode <= KEY_9:
		return int(keycode - KEY_1)

	if keycode == KEY_0:
		return 9

	return -1


func _switch_to_scene(scene_index: int) -> void:
	if scene_index < 0 or scene_index >= scene_shortcuts.size():
		return

	var scene_path := scene_shortcuts[scene_index]
	if scene_path.is_empty():
		return

	if get_tree().current_scene and get_tree().current_scene.scene_file_path == scene_path:
		return

	var previous_scene_path := _current_scene_path()
	_log_telemetry_event("scene_transition", {"action": "switch", "info": "from_%s_to_%s" % [previous_scene_path, scene_path]})
	if telemetry_session_active:
		_stop_telemetry_session("scene_switch")

	get_tree().change_scene_to_file(scene_path)

	print("Switched to scene: ", scene_index + 1, " - ", scene_shortcuts[scene_index])


# Update the timer display label
func _update_timer_display() -> void:
	timer_label.text = "%.2f" % elapsed_time


# Called when the player reaches victory height
func _on_victory() -> void:
	is_timer_running = false
	victory_reached = true
	_set_victory_ui()
	print("Victory! Final time: %.2f seconds" % elapsed_time)
	_update_timer_display()
	$"OSCClient - OUT".send_message("/player/victory", [elapsed_time])


# Reset player position and timer to initial state
func _reset_player() -> void:
	global_position = start_position
	velocity = Vector2.ZERO
	elapsed_time = 0.0
	is_timer_running = false
	is_jump_held = false
	jump_hold_boost = 0.0
	victory_reached = false
	_update_timer_display()
	_set_prompt_ui()
	reset = true
	print("Player and timer reset!")
	coin_counter_label.text = "0"
	coin_counter_label.visible = true


func _set_prompt_ui() -> void:
	status_label.visible = true
	status_label.text = "Get to the top!"
	score_label.visible = false
	coin_counter_label.visible = false


func _set_running_ui() -> void:
	status_label.visible = false
	score_label.visible = false
	coin_counter_label.visible = true


func _set_victory_ui() -> void:
	status_label.visible = false
	score_label.visible = true


func _is_jump_enabled_in_current_scene() -> bool:
	if jump_enabled_scenes.is_empty():
		return true

	var current_scene := get_tree().current_scene
	if not current_scene:
		return false

	return current_scene.scene_file_path in jump_enabled_scenes


func _is_godot_muted_in_current_scene() -> bool:
	var current_scene := get_tree().current_scene
	if not current_scene:
		return false

	return current_scene.scene_file_path in godot_muted_scenes


func _is_scene_6_active() -> bool:
	var current_scene := get_tree().current_scene
	if not current_scene:
		return false

	return current_scene.scene_file_path == "res://Scenes/Main/scene-6.tscn"


func _is_scene_7_active() -> bool:
	var current_scene := get_tree().current_scene
	if not current_scene:
		return false

	return current_scene.scene_file_path == "res://Scenes/Main/scene-7.tscn"


func _apply_godot_scene_mute() -> void:
	if _is_godot_muted_in_current_scene():
		AudioServer.set_bus_volume_db(0, -INF)
		master_bus_muted = true
		if wind_sfx and wind_sfx.playing:
			wind_sfx.stop()
		print("Godot audio muted for scene: ", get_tree().current_scene.scene_file_path)
	else:
		AudioServer.set_bus_volume_db(0, -2)
		master_bus_muted = false


func _ensure_panner_bus(bus_name: String) -> AudioEffectPanner:
	var bus_index := AudioServer.get_bus_index(bus_name)
	if bus_index == -1:
		AudioServer.add_bus()
		bus_index = AudioServer.get_bus_count() - 1
		AudioServer.set_bus_name(bus_index, bus_name)
		AudioServer.set_bus_send(bus_index, "Master")

	if AudioServer.get_bus_effect_count(bus_index) == 0 or not (AudioServer.get_bus_effect(bus_index, 0) is AudioEffectPanner):
		while AudioServer.get_bus_effect_count(bus_index) > 0:
			AudioServer.remove_bus_effect(bus_index, 0)
		var panner := AudioEffectPanner.new()
		AudioServer.add_bus_effect(bus_index, panner, 0)
		return panner

	return AudioServer.get_bus_effect(bus_index, 0) as AudioEffectPanner


func _configure_scene_variation_audio() -> void:
	if not (_is_scene_6_active() or _is_scene_7_active()):
		return

	jump_vari_panner = _ensure_panner_bus(JUMP_VARI_BUS)
	land_vari_panner = _ensure_panner_bus(LAND_VARI_BUS)
	wind_vari_panner = _ensure_panner_bus(WIND_VARI_BUS)

	if jump_sfx_1_vari:
		jump_sfx_1_vari.bus = JUMP_VARI_BUS
	if land_sfx_1_vari:
		land_sfx_1_vari.bus = LAND_VARI_BUS
	if wind_sfx:
		wind_sfx.bus = WIND_VARI_BUS


func _randomize_event_pan(panner: AudioEffectPanner, scene_6_amount: float, scene_7_amount: float) -> void:
	if not panner:
		return

	if _is_scene_6_active():
		panner.pan = randf_range(-scene_6_amount, scene_6_amount)
	elif _is_scene_7_active():
		panner.pan = randf_range(-scene_7_amount, scene_7_amount)
	else:
		panner.pan = 0.0


func _play_wind_with_scene_offset() -> void:
	if not wind_sfx:
		return

	var stream_length := 0.0
	if wind_sfx.stream:
		stream_length = wind_sfx.stream.get_length()

	if stream_length <= 0.0:
		wind_sfx.play()
		return

	if _is_scene_6_active():
		wind_sfx.play(randf_range(0.0, stream_length * 0.85))
	elif _is_scene_7_active():
		wind_sfx.play(randf_range(0.0, stream_length * 0.35))
	else:
		wind_sfx.play()


# Adds the player's jump velocity if able
func jump():
	
	if not _is_jump_enabled_in_current_scene():
		return
	
	if coyote_timer.time_left > 0.0:
		coyote_timer.stop()
		is_jump_held = true
		jump_hold_boost = 0.0
		
		# Set initial jump velocity to minimum if variable jump is enabled
		if variable_jump_height:
			velocity.y = -(minimum_jump_height / jump_time_to_peak * 2.0)
		else:
			velocity.y = jump_velocity

		if not _is_godot_muted_in_current_scene() and wind_sfx:
			if not wind_sfx.playing:
				_play_wind_with_scene_offset()
			# Immediate audible base level on jump so wind is heard right away.
			wind_sfx.volume_db = maxf(wind_sfx.volume_db, -16.0)
		
		_log_telemetry_event("jump_executed", {"action": "jump", "info": "x_%s_y_%s" % [position.x, position.y]})
		
		if debug_osc_msg:
			print("Player Jumped at position: ", position)
		$"OSCClient - OUT".send_message("/player/jump", [1])
		peak_reached = false


		
		# play jump sfx static sample
		if not _is_godot_muted_in_current_scene() and jump_sfx_1:
			jump_sfx_1.play()
			
		if not _is_godot_muted_in_current_scene() and jump_sfx_1_vari:
			_randomize_event_pan(jump_vari_panner, 0.35, 0.08)
			# Scene 6 gets stronger random modulation than the default scenes.
			if _is_scene_6_active():
				jump_sfx_1_vari.pitch_scale = randf_range(0.5, 1.85)
				jump_sfx_1_vari.volume_db = randf_range(-4.0, 1.0)
			elif _is_scene_7_active():
				jump_sfx_1_vari.pitch_scale = randf_range(0.98, 1.02)
				jump_sfx_1_vari.volume_db = randf_range(-5.2, -4.8)
			else:
				jump_sfx_1_vari.pitch_scale = randf_range(0.8, 1.2)
			jump_sfx_1_vari.play()
		
	
	if _get_gravity(velocity) == fall_gravity:
		jump_buffer_timer.start()


# Stops jump acceleration if variable_jump_height is enabled
func jump_cut():
	is_jump_held = false
	jump_hold_boost = 0.0
	
	if not variable_jump_height:
		return
	
	# Limit jump height to minimum if released early
	if velocity.y < -minimum_jump_height:
		velocity.y = -minimum_jump_height

# function that runs when player lands
# Sends velocity and surface data to MAX for folio synthesis using SDT (Sound Design Toolkit)
func _on_landed(landing_velocity: Vector2, surface_tag: String):

	_check_tile_type_on_land()
	_log_platform_landing()
	_log_telemetry_event("landed", {"action": "land", "info": "surface_%s_impact_%s" % [surface_tag, str(clamp(abs(landing_velocity.y) / max_fall_speed, 0.0, 10.0))]})
	

	# Calculate impact energy from vertical velocity (0.0 to 1.0)
	var impact_energy = clamp(abs(landing_velocity.y) / max_fall_speed, 0.0, 10.0)
	
	# Send to MAX/SDT:
	# - Strike velocity: use negative vertical velocity for impact intensity
	$"OSCClient - OUT".send_message("/sdt/strike", [-landing_velocity.y, impact_energy])
	
	# - Surface type affects modal frequencies and decay times
	$"OSCClient - OUT".send_message("/sdt/surface", [surface_tag])
	
	# - Horizontal velocity for directional folio cues
	$"OSCClient - OUT".send_message("/sdt/direction", [sign(landing_velocity.x)])
	
	print("Player Landed - Impact Energy: %.2f" % impact_energy)
	$"OSCClient - OUT".send_message("/player/impact_energy", [impact_energy])
	$"OSCClient - OUT".send_message("/player/landed", [1])

	# also send tile type
	$"OSCClient - OUT".send_message("/player/tile_type", [surface_tag])
	
	# send player height to MAX
	$"OSCClient - OUT".send_message("/player/height", [global_position.y])
	
	# play landing sfx static sample
	if not _is_godot_muted_in_current_scene() and land_sfx_1_vari:
		_randomize_event_pan(land_vari_panner, 0.4, 0.1)
		# Scene 6 gets wider variation on top of impact-driven volume.
		if _is_scene_6_active():
			land_sfx_1_vari.pitch_scale = randf_range(0.4, 1.9)
			land_sfx_1_vari.volume_db = lerp(-16.0, -4.0, impact_energy) + randf_range(-2.0, 2.0)
		elif _is_scene_7_active():
			land_sfx_1_vari.pitch_scale = randf_range(0.98, 1.02)
			land_sfx_1_vari.volume_db = lerp(-5.2, -4.0, impact_energy) + randf_range(-0.2, 0.2)
		else:
			land_sfx_1_vari.pitch_scale = randf_range(0.7, 1)
			# adjust volume based on impact energy (0.0 to 1.0)
			land_sfx_1_vari.volume_db = lerp(-5.0, -2.0, impact_energy)
		land_sfx_1_vari.play()
		
var last_landed_tiles = []
var repeat_left = true
var repeat_right = true


func _check_tile_id_on_land():
	print(last_landed_tiles)
	
	if last_landed_tiles.size() >= 3:
		var x = 1
		while x < last_landed_tiles.size():
			if last_landed_tiles[x][1][0] < last_landed_tiles[x - 1][1][0]:
				repeat_right = false
			if last_landed_tiles[x][1][0] > last_landed_tiles[x - 1][1][0]:
				repeat_left = false
				
			x += 1 
			# TODO check if any are matching, then sett false
			
		if repeat_left:
			$"OSCClient - OUT".send_message("/player/repeat_left", [1])
			
		if repeat_right:
			$"OSCClient - OUT".send_message("/player/repeat_right", [1])
			
		# reset
		last_landed_tiles = []
		repeat_left = true
		repeat_right = true
		

func _log_platform_landing() -> void:
	var collision := get_last_slide_collision()
	if not collision:
		return

	var tile_map := collision.get_collider() as TileMapLayer
	if not tile_map:
		return

	# Move one pixel into the colliding tile before converting to map coordinates.
	# This avoids classifying a contact on a tile boundary as the empty cell above it.
	var tile_world_position := collision.get_position() - collision.get_normal()
	var tile_coordinates := tile_map.local_to_map(tile_map.to_local(tile_world_position))
	var source_id := tile_map.get_cell_source_id(tile_coordinates)
	var atlas_coordinates := tile_map.get_cell_atlas_coords(tile_coordinates)
	var scene_name := _current_scene_path().get_file().get_basename()
	var platform_id := "%s/%s/%d_%d" % [scene_name, tile_map.name, tile_coordinates.x, tile_coordinates.y]
	var info := "platform_%s_layer_%s_tile_%d_%d_source_%d_atlas_%d_%d" % [
		platform_id,
		tile_map.name,
		tile_coordinates.x,
		tile_coordinates.y,
		source_id,
		atlas_coordinates.x,
		atlas_coordinates.y
	]

	_log_telemetry_event("platform_landed", {
		"action": "land_on_platform",
		"info": info
	})
		
func _sdt_wind():
	# send player velocity to MAX/SDT for wind synthesis
	$"OSCClient - OUT".send_message("/player/wind_velocity", [velocity.y])


func _update_wind_sfx(delta: float) -> void:
	if not wind_sfx or _is_godot_muted_in_current_scene():
		return

	var is_scene_6 := _is_scene_6_active()
	var is_scene_7 := _is_scene_7_active()

	if not is_on_floor():
		var normalized_speed: float = clamp(abs(velocity.y) / max_fall_speed, 0.0, 1.0)
		var target_volume_db: float = lerp(-4.0, 10.0, normalized_speed)

		if is_scene_6:
			wind_modulation_timer -= delta
			if wind_modulation_timer <= 0.0:
				wind_modulation_timer = randf_range(0.06, 0.2)
				wind_modulation_target_db = randf_range(-3.0, 3.0)
				wind_modulation_target_pitch = randf_range(0.82, 1.22)
				wind_modulation_target_pan = randf_range(-0.4, 0.4)

			target_volume_db += wind_modulation_target_db
			wind_sfx.pitch_scale = move_toward(wind_sfx.pitch_scale, wind_modulation_target_pitch, 4.0 * delta)
			if wind_vari_panner:
				wind_vari_panner.pan = move_toward(wind_vari_panner.pan, wind_modulation_target_pan, 4.0 * delta)
		elif is_scene_7:
			wind_modulation_timer -= delta
			if wind_modulation_timer <= 0.0:
				wind_modulation_timer = randf_range(0.3, 0.6)
				wind_modulation_target_db = randf_range(-0.4, 0.4)
				wind_modulation_target_pitch = randf_range(0.98, 1.02)
				wind_modulation_target_pan = randf_range(-0.08, 0.08)

			target_volume_db += wind_modulation_target_db
			wind_sfx.pitch_scale = move_toward(wind_sfx.pitch_scale, wind_modulation_target_pitch, 1.5 * delta)
			if wind_vari_panner:
				wind_vari_panner.pan = move_toward(wind_vari_panner.pan, wind_modulation_target_pan, 1.5 * delta)
		else:
			wind_modulation_timer = 0.0
			wind_modulation_target_db = 0.0
			wind_modulation_target_pitch = 1.0
			wind_modulation_target_pan = 0.0
			wind_sfx.pitch_scale = move_toward(wind_sfx.pitch_scale, 1.0, 4.0 * delta)
			if wind_vari_panner:
				wind_vari_panner.pan = move_toward(wind_vari_panner.pan, 0.0, 3.0 * delta)

		wind_sfx.volume_db = move_toward(wind_sfx.volume_db, target_volume_db, 140.0 * delta)
		if not wind_sfx.playing:
			_play_wind_with_scene_offset()
	else:
		if is_scene_6:
			wind_sfx.pitch_scale = move_toward(wind_sfx.pitch_scale, 1.0, 6.0 * delta)
		elif is_scene_7:
			wind_sfx.pitch_scale = move_toward(wind_sfx.pitch_scale, 1.0, 3.0 * delta)
		if wind_vari_panner:
			wind_vari_panner.pan = move_toward(wind_vari_panner.pan, 0.0, 3.0 * delta)
		wind_sfx.volume_db = move_toward(wind_sfx.volume_db, -40.0, 100.0 * delta)
		if wind_sfx.playing and wind_sfx.volume_db <= -39.5:
			wind_sfx.stop()
			
func _play_footstep():
	var foot_position = global_position + Vector2(0, footstep_probe_down)
	FootStepSoundManager.play_footstep(foot_position)

# possible surfaces: var tile_types = ["cloud", "grass", "dirt", "snow", "mushroom", "water_tube", "leaves"]

# function to check what tile type the player landed on
# on land, send a bang to max over OSC to mark first impackt
func _check_tile_type_on_land():
	var collision := get_last_slide_collision()
	if not collision:
		return

	var tile_type := FootStepSoundManager.get_tile_type(collision.get_position())
	$"OSCClient - OUT".send_message("/player/landed/" + tile_type, [1])

	if debug_osc_msg:
		print("OSC Sent /player/landed/" + tile_type)
		
		

# function to check what tile type the player is walking on
# send a bang when starting walk on a tile, abd send a bang when leaving/stopping walking a tile
func _walking_on_tile():
	var is_walking := is_on_floor() and absf(velocity.x) > 0.1
	var current_tile_type := ""

	if is_walking:
		var foot_position := global_position + Vector2(0, footstep_probe_down)
		current_tile_type = FootStepSoundManager.get_tile_type(foot_position)

	if walking_tile_type != current_tile_type:
		if not walking_tile_type.is_empty():
			$"OSCClient - OUT".send_message("/player/running/" + walking_tile_type, [0])

		walking_tile_type = current_tile_type

		if not walking_tile_type.is_empty():
			$"OSCClient - OUT".send_message("/player/running/" + walking_tile_type, [1])

			print("TEST OSC Sent /player/running/" + walking_tile_type)

# function to check if the player is colliding with anything
func _is_on_wall() -> bool:
	var collision := get_last_slide_collision()
	if not collision:
		return false
	
	return collision.get_collider() != null
