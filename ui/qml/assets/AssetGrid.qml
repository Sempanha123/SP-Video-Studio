import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
GridView {
    id: root
    property var assets: []
    signal selected(string assetId)
    model: assets
    cellWidth: Math.max(190, width / Math.max(1, Math.floor(width / 210)))
    cellHeight: 198
    clip: true; reuseItems: true
    delegate: Item {
        required property var modelData
        width: root.cellWidth; height: root.cellHeight
        AssetCard { anchors.fill: parent; anchors.margins: 6; asset: modelData; onSelected: function(id){ root.selected(id) } }
    }
}
