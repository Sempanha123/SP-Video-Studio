import QtQuick 2.15
import QtQuick.Controls 2.15
Item {
    anchors.fill: parent
    z: 10000
    RecoveryStatus { anchors.top: parent.top; anchors.right: parent.right; anchors.topMargin: 18; anchors.rightMargin: 180 }
    RecoveryDialog { id: recoveryDialog; parent: Overlay.overlay }
}
