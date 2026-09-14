import QtQuick 2.15
import QtQuick.Controls 2.15
import SPVideoStudio.Updates 1.0

Item {
    id: root
    anchors.fill: parent
    z: 10000
    UpdateAvailableDialog { id: available; parent: Overlay.overlay }
    Timer {
        interval: 2500
        running: Updates.configured && Updates.automaticCheck
        repeat: false
        onTriggered: Updates.checkForUpdates()
    }
    Connections { target: Updates; function onUpdateAvailable() { available.open() } }
}
