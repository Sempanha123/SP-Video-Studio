import QtQuick 2.15
import QtQuick.Controls 2.15
import "../theme"

Slider {
    id: root
    property var controller

    from: 0
    to: controller ? Math.max(1, controller.duration) : 1
    enabled: controller ? controller.seekEnabled : false
    value: 0

    function syncPosition() {
        if (!pressed && controller)
            value = controller.position
    }

    Component.onCompleted: syncPosition()
    onMoved: { }
    onPressedChanged: {
        if (!pressed && controller && enabled)
            controller.seek(Math.round(value))
    }

    Connections {
        target: root.controller
        ignoreUnknownSignals: true
        function onPlaybackChanged() { root.syncPosition() }
        function onSelectedMediaChanged() { root.syncPosition() }
    }

    background: Rectangle {
        x: root.leftPadding
        y: root.topPadding + root.availableHeight / 2 - height / 2
        width: root.availableWidth
        height: 4
        radius: 2
        color: Theme.colors.borderStrong
        Rectangle {
            width: root.visualPosition * parent.width
            height: parent.height
            radius: parent.radius
            color: Theme.colors.accent
        }
    }

    handle: Rectangle {
        x: root.leftPadding + root.visualPosition * (root.availableWidth - width)
        y: root.topPadding + root.availableHeight / 2 - height / 2
        implicitWidth: root.pressed ? 14 : 12
        implicitHeight: implicitWidth
        radius: width / 2
        color: root.enabled ? Theme.colors.accent : Theme.colors.textMuted
        border.width: 2
        border.color: Theme.colors.surfaceRaised
        Behavior on implicitWidth { NumberAnimation { duration: Theme.animation.fast } }
    }
}
