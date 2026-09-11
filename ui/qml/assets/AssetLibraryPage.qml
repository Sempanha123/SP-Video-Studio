import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import QtQuick.Dialogs
import SPVideoStudio.Phase25 1.0
import "../theme"
import "../components"
Item {
    id: root
    signal toastRequested(string message,string variant)
    AssetImportDialog { id:importDialog }
    AssetRelinkDialog { id:relinkDialog }
    FolderDialog { id:libraryFolder; title:"Move Managed Asset Library"; onAccepted:AssetLibrary.migrateLibrary(selectedFolder,"move") }
    ColumnLayout { anchors.fill:parent; spacing:Theme.spacing.md
        RowLayout { Layout.fillWidth:true
            ColumnLayout { Layout.fillWidth:true; spacing:2
                Text { text:"Reusable Asset Library"; color:Theme.colors.textPrimary; font.family:Theme.type.family; font.pixelSize:Theme.type.titleLarge; font.weight:Theme.type.semibold }
                Text { text:"Global reusable media stays separate from Project Media. Drag an asset into a project Timeline or add it explicitly."; color:Theme.colors.textSecondary; font.family:Theme.type.family; font.pixelSize:Theme.type.bodySmall; wrapMode:Text.WordWrap; Layout.fillWidth:true }
            }
            SecondaryButton { text:"Library Location"; onClicked:libraryFolder.open() }
            SecondaryButton { text:"Refresh"; onClicked:AssetLibrary.refresh() }
            SecondaryButton { text:"Reference"; onClicked:importDialog.openReferenced() }
            AppButton { text:"Import Copy"; iconName:"plus"; onClicked:importDialog.openManaged() }
        }
        AssetFilterBar { Layout.fillWidth:true; onQueryChanged:function(v){AssetLibrary.setQuery(v)}; onFilterChanged:function(v){AssetLibrary.setFilter(v)}; onSortChanged:function(v){AssetLibrary.setSort(v)} }
        SplitView { Layout.fillWidth:true; Layout.fillHeight:true
            AssetCollectionSidebar { SplitView.preferredWidth:190; SplitView.minimumWidth:160; collections:AssetLibrary.collections; onCollectionSelected:function(id){AssetLibrary.setCollection(id)} }
            AssetGrid { SplitView.fillWidth:true; SplitView.fillHeight:true; assets:AssetLibrary.assets; onSelected:function(id){AssetLibrary.selectAsset(id)} }
            AppCard { SplitView.preferredWidth:300; SplitView.minimumWidth:260; SplitView.fillHeight:true; AssetInspector { anchors.fill:parent; anchors.margins:Theme.spacing.lg; asset:AssetLibrary.selectedAsset; onRelinkRequested:function(id){relinkDialog.openFor(id)} } }
        }
    }
    Connections { target:AssetLibrary; function onOperationSucceeded(message){root.toastRequested(message,"success")} function onOperationFailed(message){root.toastRequested(message,"error")} }
}
