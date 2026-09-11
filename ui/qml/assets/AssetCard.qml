import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../theme"
import "../components"
AppCard {
    id: root
    property var asset: ({})
    property string assetId: asset.id || ""
    property string mediaType: asset.type || ""
    property string assetSubtype: asset.subtype || ""
    signal selected(string assetId)
    implicitHeight: 196
    interactive: true
    onClicked: root.selected(root.assetId)
    Drag.active: drag.active; Drag.source: root; Drag.keys: ["sp-global-asset", "sp-global-asset-" + mediaType]; Drag.supportedActions: Qt.CopyAction
    DragHandler { id: drag; target: null }
    ColumnLayout {
        anchors.fill: parent; anchors.margins: Theme.spacing.sm; spacing: Theme.spacing.sm
        Rectangle {
            Layout.fillWidth: true; Layout.preferredHeight: 112; radius: Theme.radius.medium; color: Theme.colors.surfaceHover; clip: true
            Image { anchors.fill: parent; fillMode: Image.PreserveAspectCrop; source: asset.thumbnailResolved ? "file:///" + asset.thumbnailResolved : ""; sourceSize.width: 320; sourceSize.height: 180; visible: status === Image.Ready; asynchronous: true; cache: true }
            Icon { anchors.centerIn: parent; width: 25; height: 25; name: mediaType === "audio" ? "mic" : (mediaType === "image" ? "image" : "video"); opacity: 0.65 }
            Rectangle { anchors.left: parent.left; anchors.top: parent.top; anchors.margins: 7; radius: 6; width: badge.implicitWidth + 12; height: 22; color: Theme.colors.elevated; opacity: 0.94
                Text { id: badge; anchors.centerIn: parent; text: (asset.subtype || mediaType).replaceAll("_", " "); color: Theme.colors.textSecondary; font.family: Theme.type.family; font.pixelSize: Theme.type.caption }
            }
            Rectangle { visible: asset.favorite; anchors.right: parent.right; anchors.top: parent.top; anchors.margins: 7; width: 24; height: 24; radius: 7; color: Theme.colors.warningSoft
                Text { anchors.centerIn: parent; text: "★"; color: Theme.colors.warning; font.pixelSize: 12 }
            }
            Text { anchors.right: parent.right; anchors.bottom: parent.bottom; anchors.margins: 7; visible: Number(asset.durationMs || 0) > 0; text: Math.floor(Number(asset.durationMs || 0)/1000) + "s"; color: "#E7E8ED"; font.family: Theme.type.family; font.pixelSize: Theme.type.caption }
        }
        Text { Layout.fillWidth: true; text: asset.name || "Asset"; elide: Text.ElideRight; color: Theme.colors.textPrimary; font.family: Theme.type.family; font.pixelSize: Theme.type.bodySmall; font.weight: Theme.type.semibold }
        RowLayout { Layout.fillWidth: true; spacing: Theme.spacing.xs
            StatusBadge { text: asset.status === "missing" ? "Missing" : "Ready"; status: asset.status === "missing" ? "missing" : "ready" }
            Text { Layout.fillWidth: true; text: asset.managed ? "Managed" : "Referenced"; elide: Text.ElideRight; color: Theme.colors.textMuted; font.family: Theme.type.family; font.pixelSize: Theme.type.caption }
        }
    }
}
