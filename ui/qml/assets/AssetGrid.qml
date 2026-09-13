import QtQuick 2.15
import QtQuick.Controls 2.15
import "../theme"
import "../components"
GridView {
    id: root
    property var assets: []
    property bool hasMore: false
    property bool loadRequested: false
    signal selected(string assetId)
    signal loadMoreRequested()
    signal importRequested()
    Accessible.role: Accessible.List
    Accessible.name: "Asset Library"
    model: assets
    cellWidth: Math.max(188, width / Math.max(1, Math.floor(width / 208)))
    cellHeight: 210
    clip: true; reuseItems: true; cacheBuffer: 420
    boundsBehavior: Flickable.StopAtBounds
    onCountChanged: loadRequested = false
    onContentYChanged: {
        if (hasMore && !loadRequested && contentY + height >= contentHeight - cellHeight * 2) {
            loadRequested = true
            loadMoreRequested()
        }
    }
    delegate: Item { required property var modelData; width: root.cellWidth; height: root.cellHeight; AssetCard { anchors.fill: parent; anchors.margins: 6; asset: modelData; onSelected: function(id){ root.selected(id) } } }
    FriendlyEmptyState {
        anchors.centerIn: parent
        visible: root.count === 0
        title: "No reusable assets yet"
        description: "Import video, image or audio once, then reuse it across projects."
        iconName: "assets"
        action: AppButton { text: "Import Asset"; onClicked: root.importRequested() }
    }
}
