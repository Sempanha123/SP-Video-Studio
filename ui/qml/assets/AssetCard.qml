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
    signal selected(string assetId)
    implicitHeight: 184
    Drag.active: drag.active
    Drag.source: root
    Drag.keys: ["sp-global-asset", "sp-global-asset-" + mediaType]
    Drag.supportedActions: Qt.CopyAction
    DragHandler { id: drag; target: null }
    ColumnLayout {
        anchors.fill: parent; anchors.margins: Theme.spacing.md; spacing: Theme.spacing.sm
        Rectangle {
            Layout.fillWidth: true; Layout.preferredHeight: 96; radius: Theme.radius.medium; color: Theme.colors.surfaceHover; clip: true
            Image { anchors.fill: parent; anchors.margins: 2; fillMode: Image.PreserveAspectCrop; source: asset.thumbnailResolved ? "file:///" + asset.thumbnailResolved : ""; visible: status === Image.Ready }
            Icon { anchors.centerIn: parent; width: 26; height: 26; name: mediaType === "audio" ? "mic" : (mediaType === "image" ? "image" : "video") }
            Rectangle { anchors.left: parent.left; anchors.top: parent.top; anchors.margins: 6; radius: 5; width: badge.implicitWidth+10; height: 21; color: Theme.colors.background
                Text { id: badge; anchors.centerIn: parent; text: (asset.subtype || mediaType).replaceAll("_"," "); color: Theme.colors.textSecondary; font.family: Theme.type.family; font.pixelSize: 10 }
            }
            Text { anchors.right: parent.right; anchors.bottom: parent.bottom; anchors.margins: 6; visible: Number(asset.durationMs||0)>0; text: Math.floor(Number(asset.durationMs||0)/1000)+"s"; color: Theme.colors.textPrimary; font.pixelSize: 10 }
        }
        RowLayout { Layout.fillWidth: true
            Text { Layout.fillWidth: true; text: asset.name || "Asset"; elide: Text.ElideRight; color: Theme.colors.textPrimary; font.family: Theme.type.family; font.pixelSize: Theme.type.bodySmall; font.weight: Theme.type.semibold }
            Text { text: asset.favorite ? "★" : ""; color: Theme.colors.warning; font.pixelSize: 14 }
        }
        Text { Layout.fillWidth: true; text: (asset.managed ? "Managed" : "Referenced") + " · " + (asset.status || "ready"); elide: Text.ElideRight; color: asset.status === "missing" ? Theme.colors.danger : Theme.colors.textMuted; font.family: Theme.type.family; font.pixelSize: Theme.type.caption }
    }
    TapHandler { onTapped: root.selected(root.assetId) }
}
