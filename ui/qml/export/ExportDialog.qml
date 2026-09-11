import QtQuick 2.15

Item {
    id: root
    property var controller
    ExportPage { anchors.fill: parent; controller: root.controller }
}
