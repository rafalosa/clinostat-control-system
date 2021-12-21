from chamber.modules import chamber_controller as cc
import modules.sensors as sen


if __name__ == "__main__":

    controller = cc.ChamberController()

    camera1 = sen.Camera("videoCam1", "1280x720")
    camera2 = sen.Camera("videoCam2", "1280x720")

    controller.attach_camera(camera1)
    controller.attach_camera(camera2)
    controller.add_server_connection()
    controller.add_worker_pin(5)
    controller.add_light_control(6, 7)
    controller.start()  # Can be started on another thread.
