import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import SPVideoStudio.Phase25 1.0
import "../theme"
import "../components"
ScrollView {
    id: root
    property var asset: ({})
    signal relinkRequested(string assetId)
    contentWidth: availableWidth
    ColumnLayout {
        width: root.availableWidth; spacing: Theme.spacing.md
        Text { text: asset.name || "Select an asset"; color: Theme.colors.textPrimary; font.family: Theme.type.family; font.pixelSize: Theme.type.heading; font.weight: Theme.type.semibold; wrapMode: Text.WordWrap; Layout.fillWidth: true }
        Image { Layout.fillWidth: true; Layout.preferredHeight: 180; source: asset.thumbnailResolved ? "file:///"+asset.thumbnailResolved : ""; fillMode: Image.PreserveAspectFit; visible: source.toString().length>0 }
        Text { visible: asset.id; text: (asset.type||"").toUpperCase()+" · "+(asset.subtype||"general").replaceAll("_"," ")+" · "+(asset.storageMode||""); color: Theme.colors.textSecondary; font.family: Theme.type.family; font.pixelSize: Theme.type.bodySmall }
        Text { visible: asset.id; text: asset.width ? asset.width+" × "+asset.height+(asset.fps ? " · "+Number(asset.fps).toFixed(2)+" FPS" : "") : ""; color:Theme.colors.textMuted; font.family:Theme.type.family; font.pixelSize:Theme.type.caption }
        Text { visible: asset.id; text: "Used in " + (asset.usageCount||0) + " project" + ((asset.usageCount||0)===1?"":"s"); color:Theme.colors.textMuted; font.family:Theme.type.family; font.pixelSize:Theme.type.caption }
        InfoBanner { Layout.fillWidth: true; visible: asset.status === "missing"; variant:"warning"; text:"The original file could not be found. Use Relink to restore every project reference." }
        RowLayout { visible: asset.id; Layout.fillWidth:true
            AppButton { text: "Add to Project"; enabled: AssetLibrary.currentProjectId.length>0; onClicked: AssetLibrary.addToCurrentProject(asset.id) }
            SecondaryButton { text: asset.favorite ? "Unfavorite" : "Favorite"; onClicked: AssetLibrary.setFavorite(asset.id,!asset.favorite) }
            SecondaryButton { visible: asset.status === "missing" && !asset.managed; text:"Relink"; onClicked:root.relinkRequested(asset.id) }
            SecondaryButton { text:"Remove"; onClicked:AssetLibrary.removeAsset(asset.id,"cancel") }
        }
        Text { visible: asset.id; text: "Tags: " + ((asset.tags||[]).join(", ") || "None"); color:Theme.colors.textSecondary; font.family:Theme.type.family; font.pixelSize:Theme.type.bodySmall; wrapMode:Text.WordWrap; Layout.fillWidth:true }
        Text { visible: asset.id; text: "Rights: " + ((asset.license||{}).rightsStatus || "unknown") + (((asset.license||{}).attributionRequired) ? " · Attribution required" : ""); color:Theme.colors.textSecondary; font.family:Theme.type.family; font.pixelSize:Theme.type.bodySmall; wrapMode:Text.WordWrap; Layout.fillWidth:true }
        Text { visible: asset.id && asset.notes; text: asset.notes || ""; color:Theme.colors.textMuted; font.family:Theme.type.family; font.pixelSize:Theme.type.bodySmall; wrapMode:Text.WordWrap; Layout.fillWidth:true }
    }
}
